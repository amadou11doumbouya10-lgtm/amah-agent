"""
Amah Agent - Conversation Search V0.2.2

Recherche hybride dans les anciennes conversations.

Objectifs :
- recherche exacte sur les mots, y compris les nouveaux noms inconnus ;
- alias / synonymes pour les concepts connus ;
- détection des expressions composées ("Amah Agent", "Vision Amah", etc.) ;
- bonus si les termes de la requête sont proches dans le message ;
- bonus pour la phrase exacte ;
- couverture des termes ;
- récence ;
- priorité légère aux messages utilisateur ;
- exclusion des messages pauvres et des traces techniques ;
- déduplication ;
- aucun changement de schéma SQLite ;
- compatible Python 3.9.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = Path(__file__).parent.parent / "amah_memory.db"

DEFAULT_LIMIT = 8
MAX_CANDIDATES = 250
MIN_CONTENT_LENGTH = 25

# Nombre maximum de mots à extraire d'une requête.
MAX_QUERY_TERMS = 10

# Nombre maximum de messages très proches conservés par contenu normalisé.
MAX_NEAR_DUPLICATES = 1


# ============================================================================
# STOP WORDS
# ============================================================================

STOP_WORDS = {
    "a", "ai", "as", "au", "aux", "avec",
    "ce", "cela", "ca", "ces", "cet", "cette",
    "comme", "dans", "de", "des", "du",
    "en", "est", "et",
    "faire",
    "il", "ils",
    "je", "la", "le", "les",
    "ma", "mais", "me", "mes", "moi", "mon",
    "ne", "nos", "notre", "nous",
    "on", "ou",
    "par", "pas", "pour",
    "que", "quel", "quelle", "quels", "quelles",
    "qui",
    "se",
    "son", "sont", "sur",
    "ta", "te", "tes", "toi", "ton",
    "tu",
    "un", "une",
    "vos", "votre", "vous",
    "y",

    # Métalangage des requêtes de mémoire.
    "avait", "avions",
    "dit", "decide", "decidee",
    "deja",
    "parle", "parler",
    "discussion", "conversation",
    "rappelle", "rappeler",
    "souviens", "souvenir",
    "sais", "savez",
    "chose", "choses",
    "question", "questions",
    "quoi", "comment", "pourquoi",
}


# ============================================================================
# ALIAS / SYNONYMES
# ============================================================================

TERM_ALIASES = {
    "router": {
        "router",
        "routeur",
        "routage",
        "toolrouter",
    },
    "amah": {
        "amah",
    },
    "agent": {
        "agent",
        "assistant",
    },
    "projet": {
        "projet",
        "projets",
    },
    "vision": {
        "vision",
    },
    "github": {
        "github",
    },
    "performance": {
        "performance",
        "performances",
        "latence",
        "lent",
        "lenteur",
        "vitesse",
        "rapide",
    },
}


# ============================================================================
# NORMALISATION
# ============================================================================

def normalize(text: str) -> str:
    """Normalise accents, casse, ponctuation et espaces."""
    text = str(text).lower().strip()

    text = unicodedata.normalize("NFD", text)

    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )

    text = text.replace("'", " ")
    text = text.replace("’", " ")

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def compact(text: str) -> str:
    """Supprime les espaces après normalisation."""
    return normalize(text).replace(" ", "")


# ============================================================================
# EXTRACTION DES TERMES
# ============================================================================

def extract_terms(
    query: str,
    max_terms: int = MAX_QUERY_TERMS,
) -> List[str]:
    text = normalize(query)

    terms: List[str] = []

    for word in text.split():
        if len(word) < 3:
            continue

        if word in STOP_WORDS:
            continue

        if word in terms:
            continue

        terms.append(word)

        if len(terms) >= max_terms:
            break

    return terms


def expand_terms(
    terms: List[str],
) -> Dict[str, Set[str]]:
    """
    Pour un terme connu, ajoute ses alias.
    Pour un terme inconnu, conserve le terme exact.

    Exemple :
        router -> {router, routeur, routage, toolrouter}
        vertex -> {vertex}
    """
    expanded: Dict[str, Set[str]] = {}

    for term in terms:
        aliases = TERM_ALIASES.get(term, {term})

        expanded[term] = {
            normalize(alias)
            for alias in aliases
            if normalize(alias)
        }

        # Toujours garder le terme d'origine.
        expanded[term].add(normalize(term))

    return expanded


# ============================================================================
# BRUIT
# ============================================================================

GENERIC_MESSAGES = {
    "salut",
    "salut amah",
    "bonjour",
    "bonjour amah",
    "bonsoir",
    "hello",
    "hello amah",
    "ok",
    "oui",
    "non",
    "merci",
    "merci amah",
    "amah",
}


def is_low_information_message(content: str) -> bool:
    normalized = normalize(content)

    if not normalized:
        return True

    if normalized in GENERIC_MESSAGES:
        return True

    if len(normalized) < MIN_CONTENT_LENGTH:
        return True

    return False


# ============================================================================
# TRACES TECHNIQUES
# ============================================================================

TOOL_TRACE_PATTERNS = [
    "<function>",
    "function>",
    "<tool>",
    "tool_call",
    "tool_result",
]


def is_tool_trace(content: str) -> bool:
    text = str(content).lower()
    return any(pattern in text for pattern in TOOL_TRACE_PATTERNS)


# ============================================================================
# MATCHING
# ============================================================================

def _term_matches(
    content: str,
    alias: str,
) -> bool:
    """
    Teste :
    1. présence sous forme normale ;
    2. présence sous forme compacte.

    Le second cas permet de trouver :
        Amah Agent
        amah-agent
        amah_agent
    """
    normalized_content = normalize(content)
    alias_normalized = normalize(alias)

    if not alias_normalized:
        return False

    # Mot / expression normalisé.
    if alias_normalized in normalized_content:
        return True

    # Forme compacte.
    return compact(alias_normalized) in compact(content)


def _term_positions(
    content: str,
    aliases: Set[str],
) -> List[int]:
    """
    Renvoie les positions des alias trouvés dans le texte.

    Une position correspond à un index de mot.
    """

    words = normalize(content).split()

    if not words:
        return []

    positions: List[int] = []

    normalized_aliases = {
        tuple(normalize(alias).split())
        for alias in aliases
        if normalize(alias)
    }

    for alias_words in normalized_aliases:

        if not alias_words:
            continue

        size = len(alias_words)

        for i in range(len(words) - size + 1):

            if tuple(words[i:i + size]) == alias_words:
                positions.append(i)

    return sorted(set(positions))

def _best_term_distance(
    content: str,
    expanded_terms: Dict[str, Set[str]],
) -> Optional[int]:
    """
    Distance minimale entre deux groupes de termes dans le message.

    Plus les groupes sont proches, meilleur sera le score.
    """
    if len(expanded_terms) < 2:
        return None

    group_positions: List[List[int]] = []

    for aliases in expanded_terms.values():
        positions = _term_positions(content, aliases)
        if not positions:
            return None
        group_positions.append(positions)

    best_distance: Optional[int] = None

    for positions_a in group_positions[0]:
        for positions_b in group_positions[1]:
            distance = abs(positions_a - positions_b)

            if best_distance is None or distance < best_distance:
                best_distance = distance

    # Pour 3+ groupes, vérifier également que les groupes sont globalement
    # regroupés. On utilise l'étendue minimale trouvée dans les positions.
    if len(group_positions) > 2:
        all_positions = sorted(
            pos
            for group in group_positions
            for pos in group
        )

        if all_positions:
            span = max(all_positions) - min(all_positions)
            if best_distance is None:
                best_distance = span
            else:
                best_distance = min(best_distance, span)

    return best_distance


# ============================================================================
# SCORE
# ============================================================================

def score_result(
    content: str,
    role: str,
    query: str,
    terms: List[str],
    expanded_terms: Dict[str, Set[str]],
    row_id: int,
    newest_id: int,
) -> Tuple[float, int, List[str]]:
    normalized_content = normalize(content)
    normalized_query = normalize(query)

    score = 0.0
    matched_term_groups = 0
    matched_groups: List[str] = []

    # ------------------------------------------------------------------------
    # Phrase complète
    # ------------------------------------------------------------------------

    if (
        len(normalized_query) >= 8
        and normalized_query in normalized_content
    ):
        score += 35.0

    # ------------------------------------------------------------------------
    # Groupes de termes / alias
    # ------------------------------------------------------------------------

    for term in terms:
        aliases = expanded_terms.get(term, {term})

        matched = any(
            _term_matches(content, alias)
            for alias in aliases
        )

        if matched:
            matched_term_groups += 1
            matched_groups.append(term)

            # Base pour chaque groupe trouvé.
            score += 8.0

    # ------------------------------------------------------------------------
    # Couverture
    # ------------------------------------------------------------------------

    if terms:
        coverage = matched_term_groups / len(terms)
        score += coverage * 12.0

    # Tous les groupes sont présents.
    if (
        len(terms) >= 2
        and matched_term_groups == len(terms)
    ):
        score += 18.0

    # ------------------------------------------------------------------------
    # Proximité
    # ------------------------------------------------------------------------

    distance = None

    if matched_term_groups >= 2:
        matched_expanded = {
            term: expanded_terms[term]
            for term in terms
            if term in matched_groups
        }

        distance = _best_term_distance(
            content,
            matched_expanded,
        )

    if distance is not None:
        if distance <= 2:
            score += 24.0
        elif distance <= 5:
            score += 18.0
        elif distance <= 10:
            score += 10.0
        elif distance <= 20:
            score += 4.0

    # ------------------------------------------------------------------------
    # Type de message
    # ------------------------------------------------------------------------

    if role == "user":
        score += 3.0
    elif role == "assistant":
        score += 1.0

    # ------------------------------------------------------------------------
    # Récence
    # ------------------------------------------------------------------------

    if newest_id > 0:
        age_ratio = row_id / newest_id

        score += max(
            0.0,
            min(
                3.0,
                age_ratio * 3.0,
            ),
        )

    return (
        score,
        matched_term_groups,
        matched_groups,
    )


# ============================================================================
# SQLITE
# ============================================================================

def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


# ============================================================================
# RECHERCHE
# ============================================================================

def search_conversations(
    query: str,
    limit: int = DEFAULT_LIMIT,
) -> List[Dict[str, Any]]:

    if limit <= 0:
        return []

    terms = extract_terms(query)

    if not terms:
        return []

    expanded_terms = expand_terms(terms)

    # ------------------------------------------------------------------------
    # Construire les variantes SQL.
    # ------------------------------------------------------------------------

    sql_conditions: List[str] = []
    params: List[Any] = []

    all_aliases: Set[str] = set()

    for aliases in expanded_terms.values():
        all_aliases.update(aliases)

    for alias in all_aliases:
        alias_normalized = normalize(alias)

        if not alias_normalized:
            continue

        # Recherche brute dans le contenu.
        sql_conditions.append("LOWER(content) LIKE ?")
        params.append("%" + alias_normalized + "%")

        # Variante compacte utile pour les mots simples.
        if " " not in alias_normalized:
            sql_conditions.append("LOWER(content) LIKE ?")
            params.append("%" + alias_normalized + "%")

    if not sql_conditions:
        return []

    where_clause = " OR ".join(sql_conditions)

    sql = f"""
        SELECT
            id,
            session_id,
            role,
            content,
            created_at
        FROM conversations
        WHERE role IN ('user', 'assistant')
          AND ({where_clause})
        ORDER BY id DESC
        LIMIT ?
    """

    params.append(MAX_CANDIDATES)

    try:
        with _connect() as conn:
            rows = conn.execute(
                sql,
                params,
            ).fetchall()

            newest = conn.execute(
                "SELECT MAX(id) FROM conversations"
            ).fetchone()

    except sqlite3.Error:
        return []

    newest_id = 0

    if newest and newest[0]:
        newest_id = int(newest[0])

    # ------------------------------------------------------------------------
    # Classement.
    # ------------------------------------------------------------------------

    results: List[Dict[str, Any]] = []

    for row in rows:
        (
            row_id,
            session_id,
            role,
            content,
            created_at,
        ) = row

        if is_low_information_message(content):
            continue

        if is_tool_trace(content):
            continue

        score, matched, matched_groups = score_result(
            content=content,
            role=role,
            query=query,
            terms=terms,
            expanded_terms=expanded_terms,
            row_id=int(row_id),
            newest_id=newest_id,
        )

        if score <= 0 or matched <= 0:
            continue

        results.append(
            {
                "id": int(row_id),
                "session_id": session_id,
                "role": role,
                "content": content,
                "created_at": created_at,
                "score": round(score, 2),
                "matched_terms": matched,
                "matched_groups": matched_groups,
            }
        )

    # ------------------------------------------------------------------------
    # Tri.
    # ------------------------------------------------------------------------

    results.sort(
        key=lambda item: (
            item["score"],
            item["matched_terms"],
            item["id"],
        ),
        reverse=True,
    )

    # ------------------------------------------------------------------------
    # Déduplication.
    # ------------------------------------------------------------------------

    final_results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for result in results:
        fingerprint = normalize(result["content"])

        if fingerprint in seen:
            continue

        seen.add(fingerprint)
        final_results.append(result)

        if len(final_results) >= limit:
            break

    return final_results


# ============================================================================
# FORMATAGE
# ============================================================================

def format_results(
    results: List[Dict[str, Any]],
    max_chars: int = 400,
) -> str:
    if not results:
        return "Aucun résultat pertinent."

    lines: List[str] = []

    for result in results:
        content = result["content"]

        if len(content) > max_chars:
            content = content[:max_chars] + "...[tronque]"

        lines.append(
            f"[{result['role']}] "
            f"{content}"
        )

    return "\n".join(lines)
