"""
Amah Agent - Memory Recall V0.2.4

Amélioration de V0.2.2 :

- mémoire structurée ;
- cache ;
- exact -> sources originales ;
- détection des sujets spécifiques ;
- fusion des mémoires ;
- suppression des doublons ;
- nettoyage intelligent des résumés ;
- conservation des informations importantes ;
- conservation des sources ;
- aucune modification du schéma SQLite ;
- compatible Python 3.9.

V0.2.3 conserve principalement :

    ancien résumé
        +
    nouveau résumé
        ↓
    détection de recouvrement
        ↓
    résumé final sans répétition

V0.2.4 ajoute :

    nouvelle information
        ↓
    détection d'une mise à jour probable
        ↓
    ancienne formulation devenue obsolète écartée
        ↓
    résumé cohérent avec l'information la plus récente
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from tools.conversation_search_v022 import (
    extract_terms,
    expand_terms,
    search_conversations,
)

from tools.memory import (
    save_memory,
    get_memories,
    delete_memory,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

SUMMARY_CATEGORY = "conversation_summary"

DEFAULT_SOURCE_LIMIT = 6
MAX_SOURCE_MESSAGES = 8
MAX_SUMMARY_MEMORIES = 50

CACHE_THRESHOLD = 0.62

MEMORY_VERSION = 2

# Version fonctionnelle du module.
# MEMORY_VERSION reste à 2 pour conserver le schéma SQLite existant.
RECALL_VERSION = "0.2.4"


# ============================================================================
# NORMALISATION
# ============================================================================

def normalize(text: str) -> str:
    text = str(text or "").lower().strip()

    text = unicodedata.normalize(
        "NFD",
        text,
    )

    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )

    text = text.replace("'", " ")
    text = text.replace("’", " ")

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def compact(text: str) -> str:
    return normalize(text).replace(
        " ",
        "",
    )


def clean_item(value: Any) -> str:
    return str(
        value or ""
    ).strip()


# ============================================================================
# EXACT
# ============================================================================

EXACT_PATTERNS = [
    r"\bexactement\b",
    r"\bmessage[s]?\s+exact[s]?\b",
    r"\btexte\s+exact\b",
    r"\bmot\s+pour\s+mot\b",
    r"\bmessage[s]?\s+original[aux]*\b",
    r"\bconversation\s+originale\b",
    r"\bhistorique\s+exact\b",
    r"\bcopie[s]?\s+exacte[s]?\b",
]

EXACT_SHOW_PATTERNS = [
    r"\bmontre\b.*\bmessage[s]?\b",
    r"\bmontre\b.*\btexte\b",
    r"\bmontre\b.*\bhistorique\b",
    r"\bdonne\b.*\bmessage[s]?\b",
    r"\bdonne\b.*\btexte\b",
    r"\blis\b.*\bmessage[s]?\b",
]


def wants_exact_sources(query: str) -> bool:
    text = normalize(query)

    for pattern in EXACT_PATTERNS:
        if re.search(pattern, text):
            return True

    for pattern in EXACT_SHOW_PATTERNS:
        if re.search(pattern, text):
            return True

    return False


# ============================================================================
# TERMES
# ============================================================================

def query_terms(query: str) -> List[str]:
    return extract_terms(query)


# ============================================================================
# MÉMOIRES STRUCTURÉES
# ============================================================================

def normalize_memory_items(
    raw: Any,
) -> List[Dict[str, Any]]:

    if raw is None:
        return []

    if isinstance(raw, list):
        return [
            item
            for item in raw
            if isinstance(item, dict)
        ]

    if isinstance(raw, tuple):
        return [
            item
            for item in raw
            if isinstance(item, dict)
        ]

    if isinstance(raw, dict):

        if "content" in raw:
            return [raw]

        return [
            value
            for value in raw.values()
            if isinstance(value, dict)
        ]

    return []


def parse_structured_memory(
    memory: Dict[str, Any],
) -> Optional[Dict[str, Any]]:

    if not isinstance(memory, dict):
        return None

    content = memory.get(
        "content"
    )

    if isinstance(content, dict):
        data = dict(content)

    else:

        try:
            data = json.loads(
                str(content or "")
            )
        except Exception:
            return None

    if not isinstance(data, dict):
        return None

    if data.get("version") != MEMORY_VERSION:
        return None

    data["_memory_id"] = memory.get(
        "id"
    )

    return data


def load_structured_memories() -> List[Dict[str, Any]]:

    try:

        raw = get_memories(
            SUMMARY_CATEGORY
        )

    except TypeError:

        try:

            raw = get_memories(
                category=SUMMARY_CATEGORY
            )

        except Exception:
            return []

    except Exception:
        return []

    results = []

    for item in normalize_memory_items(raw):

        category = item.get(
            "category"
        )

        if (
            category
            and category != SUMMARY_CATEGORY
        ):
            continue

        parsed = parse_structured_memory(
            item
        )

        if parsed:
            results.append(
                parsed
            )

    return results[:MAX_SUMMARY_MEMORIES]


# ============================================================================
# TEXTE RECHERCHABLE
# ============================================================================

def memory_search_text(
    memory: Dict[str, Any],
) -> str:

    parts = [
        memory.get("topic", ""),
        memory.get("summary", ""),
        memory.get("state", ""),
    ]

    parts.extend(
        memory.get("decisions", []) or []
    )

    parts.extend(
        memory.get("facts", []) or []
    )

    parts.extend(
        memory.get("keywords", []) or []
    )

    return normalize(
        " ".join(
            str(item)
            for item in parts
            if item
        )
    )


# ============================================================================
# SUJET
# ============================================================================

def topic_specificity(
    memory: Dict[str, Any],
) -> float:

    topic = normalize(
        memory.get("topic", "")
    )

    if not topic:
        return 0.0

    count = len(
        topic.split()
    )

    if count <= 1:
        return 0.25

    if count == 2:
        return 0.60

    if count == 3:
        return 0.82

    return 1.0


def _tokens_similar(
    a: str,
    b: str,
) -> bool:

    a = normalize(a)
    b = normalize(b)

    if not a or not b:
        return False

    if a == b:
        return True

    if len(a) > 4 and a.endswith("s"):
        a = a[:-1]

    if len(b) > 4 and b.endswith("s"):
        b = b[:-1]

    return a == b


def _topic_match_strength(
    query: str,
    topic: str,
) -> float:

    query_words = normalize(
        query
    ).split()

    topic_words = normalize(
        topic
    ).split()

    if not query_words or not topic_words:
        return 0.0

    matched = 0

    for topic_word in topic_words:

        if any(
            _tokens_similar(
                topic_word,
                query_word,
            )
            for query_word in query_words
        ):
            matched += 1

    coverage = (
        matched
        / len(topic_words)
    )

    if coverage == 1.0:

        if len(topic_words) >= 2:
            return 0.50

        return 0.30

    if coverage >= 0.5:
        return 0.12

    return 0.0


# ============================================================================
# SCORE
# ============================================================================

def score_memory(
    query: str,
    memory: Dict[str, Any],
) -> float:

    terms = query_terms(
        query
    )

    if not terms:
        return 0.0

    searchable = memory_search_text(
        memory
    )

    if not searchable:
        return 0.0

    topic = normalize(
        memory.get("topic", "")
    )

    matched = 0
    topic_matched = 0

    for term in terms:

        aliases = expand_terms(
            [term]
        ).get(
            term,
            {term},
        )

        found_memory = False
        found_topic = False

        for alias in aliases:

            alias_norm = normalize(
                alias
            )

            if not alias_norm:
                continue

            if alias_norm in searchable:
                found_memory = True

            if alias_norm in topic:
                found_topic = True

        if not found_memory:

            for memory_word in searchable.split():

                if _tokens_similar(
                    term,
                    memory_word,
                ):
                    found_memory = True
                    break

        if found_memory:
            matched += 1

        if found_topic:
            topic_matched += 1

    if matched == 0:
        return 0.0

    coverage = (
        matched
        / len(terms)
    )

    topic_coverage = (
        topic_matched
        / len(terms)
    )

    score = (
        coverage * 0.55
        + topic_coverage * 0.25
    )

    score += _topic_match_strength(
        query,
        topic,
    )

    normalized_query = normalize(
        query
    )

    if (
        normalized_query
        and normalized_query == topic
    ):
        score += 0.20

    if len(terms) >= 2:

        score += (
            topic_specificity(
                memory
            )
            * 0.10
        )

    return round(
        max(
            0.0,
            min(
                1.0,
                score,
            ),
        ),
        4,
    )


def find_best_memory(
    query: str,
) -> Optional[Dict[str, Any]]:

    memories = load_structured_memories()

    if not memories:
        return None

    ranked = []

    for memory in memories:

        score = score_memory(
            query,
            memory,
        )

        if score >= CACHE_THRESHOLD:

            ranked.append(
                (
                    score,
                    topic_specificity(
                        memory
                    ),
                    memory,
                )
            )

    if not ranked:
        return None

    ranked.sort(
        key=lambda item: (
            item[0],
            item[1],
        ),
        reverse=True,
    )

    score, specificity, memory = ranked[0]

    result = dict(
        memory
    )

    result["_score"] = score
    result["_specificity"] = specificity

    return result


find_structured_memory = find_best_memory


# ============================================================================
# SOURCES
# ============================================================================

def find_sources(
    query: str,
    limit: int = DEFAULT_SOURCE_LIMIT,
) -> List[Dict[str, Any]]:

    limit = max(
        1,
        min(
            int(limit),
            MAX_SOURCE_MESSAGES,
        ),
    )

    return search_conversations(
        query=query,
        limit=limit,
    )


def get_source_ids(
    sources: List[Dict[str, Any]],
) -> List[int]:

    result = []

    for source in sources:

        try:
            value = int(
                source.get("id")
            )
        except Exception:
            continue

        if value not in result:
            result.append(value)

    return result


def get_memory_source_ids(
    memory: Dict[str, Any],
) -> List[int]:

    values = memory.get(
        "source_ids"
    ) or []

    if not isinstance(
        values,
        list,
    ):
        return []

    result = []

    for value in values:

        try:
            value = int(value)
        except Exception:
            continue

        if value not in result:
            result.append(value)

    return result


def has_new_sources(
    memory: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> bool:

    old_ids = set(
        get_memory_source_ids(
            memory
        )
    )

    new_ids = set(
        get_source_ids(
            sources
        )
    )

    return bool(
        new_ids - old_ids
    )


# ============================================================================
# NETTOYAGE DES PHRASES
# ============================================================================

def split_sentences(
    text: str,
) -> List[str]:

    text = clean_item(
        text
    )

    if not text:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    result = []

    for part in parts:

        cleaned = part.strip()

        if cleaned:
            result.append(
                cleaned
            )

    return result


def sentence_tokens(
    text: str,
) -> set:

    return set(
        word
        for word in normalize(text).split()
        if len(word) >= 3
    )


def sentence_similarity(
    a: str,
    b: str,
) -> float:

    tokens_a = sentence_tokens(
        a
    )

    tokens_b = sentence_tokens(
        b
    )

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = len(
        tokens_a & tokens_b
    )

    union = len(
        tokens_a | tokens_b
    )

    if union == 0:
        return 0.0

    return (
        intersection / union
    )


def is_redundant_sentence(
    sentence: str,
    existing: List[str],
) -> bool:

    normalized_sentence = normalize(
        sentence
    )

    if not normalized_sentence:
        return True

    for old_sentence in existing:

        old_normalized = normalize(
            old_sentence
        )

        # Phrase pratiquement identique.
        if (
            normalized_sentence
            == old_normalized
        ):
            return True

        # Une phrase contient largement l'autre.
        if (
            normalized_sentence
            in old_normalized
            or old_normalized
            in normalized_sentence
        ):
            return True

        # Très fort recouvrement lexical.
        similarity = sentence_similarity(
            sentence,
            old_sentence,
        )

        if similarity >= 0.72:
            return True

    return False


# ============================================================================
# DÉTECTION DES MISES À JOUR
# ============================================================================

CHANGE_MARKERS = {
    "desormais",
    "maintenant",
    "actuellement",
    "aujourd'hui",
    "aujourdhui",
    "a present",
    "apresent",
    "nouveau",
    "nouvelle",
    "nouveaux",
    "nouvelles",
    "change",
    "changee",
    "changee",
    "change",
    "devient",
    "devenu",
    "deviennent",
    "remplace",
    "remplacee",
    "remplacé",
    "remplacée",
    "remplaces",
    "abandonne",
    "abandonnee",
    "abandonné",
    "abandonnée",
    "cesse",
    "arrete",
    "arrête",
    "auparavant",
    "anciennement",
}

def sentence_topic_tokens(
    sentence: str,
    topic: str,
) -> set:
    tokens = sentence_tokens(sentence)
    topic_tokens = sentence_tokens(topic)
    return tokens - topic_tokens


def update_similarity(
    new_sentence: str,
    old_sentence: str,
    topic: str,
) -> float:
    """
    Mesure le recouvrement du contenu hors sujet.

    L'objectif n'est pas de détecter toutes les contradictions,
    mais d'identifier les cas où une phrase récente ressemble
    fortement à une ancienne formulation sur le même sujet.
    """
    topic_normalized = normalize(topic)

    if not topic_normalized:
        return 0.0

    topic_tokens = sentence_tokens(topic)

    # Pour un sujet générique d'un seul mot comme "Amah",
    # on évite les remplacements agressifs.
    if len(topic_tokens) < 2:
        return 0.0

    new_topic = sentence_topic_tokens(
        new_sentence,
        topic,
    )
    old_topic = sentence_topic_tokens(
        old_sentence,
        topic,
    )

    if not new_topic or not old_topic:
        return 0.0

    intersection = len(
        new_topic & old_topic
    )

    union = len(
        new_topic | old_topic
    )

    if union == 0:
        return 0.0

    return intersection / union


def contains_change_marker(
    sentence: str,
) -> bool:
    words = set(
        normalize(sentence).split()
    )

    for marker in CHANGE_MARKERS:
        marker_words = set(
            normalize(marker).split()
        )

        if marker_words.issubset(words):
            return True

    return False


def is_update_of_sentence(
    new_sentence: str,
    old_sentence: str,
    topic: str,
) -> bool:
    """
    Détermine si la nouvelle phrase semble mettre à jour
    l'ancienne plutôt que simplement ajouter un nouveau fait.

    Deux niveaux :
    - recouvrement fort du contenu sur un sujet précis ;
    - ou marqueur explicite de changement + recouvrement modéré.
    """
    topic_normalized = normalize(topic)

    if not topic_normalized:
        return False

    normalized_new = normalize(
        new_sentence
    )
    normalized_old = normalize(
        old_sentence
    )

    if (
        not normalized_new
        or not normalized_old
        or normalized_new == normalized_old
    ):
        return False

    topic_tokens = sentence_tokens(
        topic
    )

    if len(topic_tokens) < 2:
        return False

    normalized_topic = normalize(
        topic
    )

    if (
        normalized_topic not in normalize(new_sentence)
        or normalized_topic not in normalize(old_sentence)
    ):
        return False

    similarity = update_similarity(
        new_sentence,
        old_sentence,
        topic,
    )

    if similarity >= 0.45:
        return True

    if (
        similarity >= 0.20
        and contains_change_marker(new_sentence)
    ):
        return True

    return False


# ============================================================================
# FUSION DES RÉSUMÉS
# ============================================================================

def merge_summaries(
    old_summary: str,
    new_summary: str,
) -> str:
    """
    Fusionne deux résumés sans répéter les informations.

    Cas 1 :
        ancien résumé ⊂ nouveau résumé
        -> garde le nouveau

    Cas 2 :
        nouveau résumé ⊂ ancien résumé
        -> garde l'ancien

    Cas 3 :
        contenus différents
        -> fusion phrase par phrase
    """

    old_summary = clean_item(
        old_summary
    )

    new_summary = clean_item(
        new_summary
    )

    if not old_summary:
        return new_summary

    if not new_summary:
        return old_summary

    old_normalized = normalize(
        old_summary
    )

    new_normalized = normalize(
        new_summary
    )

    # Identiques.
    if old_normalized == new_normalized:
        return new_summary

    # Le nouveau contient l'ancien.
    if old_normalized in new_normalized:
        return new_summary

    # L'ancien contient le nouveau.
    if new_normalized in old_normalized:
        return old_summary

    old_sentences = split_sentences(
        old_summary
    )

    new_sentences = split_sentences(
        new_summary
    )

    # ------------------------------------------------------------
    # Construire en priorité avec le nouveau résumé.
    # ------------------------------------------------------------

    result: List[str] = []

    for sentence in new_sentences:

        if not is_redundant_sentence(
            sentence,
            result,
        ):
            result.append(
                sentence
            )

    # ------------------------------------------------------------
    # Compléter avec les informations anciennes encore uniques.
    # ------------------------------------------------------------

    topic_hint = ""

    # Le sujet n'est pas toujours disponible ici.
    # La logique de remplacement est donc activée
    # dans merge_structured_memories_local, qui appelle
    # merge_summaries_with_topic quand le topic est connu.
    for sentence in old_sentences:

        if not is_redundant_sentence(
            sentence,
            result,
        ):
            result.append(
                sentence
            )

    return " ".join(
        result
    ).strip()


def merge_summaries_with_topic(
    old_summary: str,
    new_summary: str,
    topic: str,
) -> str:
    """
    Fusion V0.2.4 avec détection de mise à jour.

    - garde le nouveau résumé en priorité ;
    - supprime les doublons ;
    - lorsqu'une phrase récente ressemble fortement
      à une ancienne formulation sur le même sujet,
      l'ancienne phrase est considérée comme obsolète.
    """
    old_summary = clean_item(
        old_summary
    )

    new_summary = clean_item(
        new_summary
    )

    if not old_summary:
        return new_summary

    if not new_summary:
        return old_summary

    old_normalized = normalize(
        old_summary
    )

    new_normalized = normalize(
        new_summary
    )

    if old_normalized == new_normalized:
        return new_summary

    if old_normalized in new_normalized:
        return new_summary

    if new_normalized in old_normalized:
        return old_summary

    old_sentences = split_sentences(
        old_summary
    )

    new_sentences = split_sentences(
        new_summary
    )

    result: List[str] = []

    # Les phrases récentes sont prioritaires.
    for sentence in new_sentences:
        if not is_redundant_sentence(
            sentence,
            result,
        ):
            result.append(
                sentence
            )

    # On garde les anciennes phrases qui apportent
    # encore une information différente.
    for old_sentence in old_sentences:

        if is_redundant_sentence(
            old_sentence,
            result,
        ):
            continue

        replaced = any(
            is_update_of_sentence(
                new_sentence=current_sentence,
                old_sentence=old_sentence,
                topic=topic,
            )
            for current_sentence in result
        )

        if replaced:
            continue

        result.append(
            old_sentence
        )

    return " ".join(
        result
    ).strip()


# ============================================================================
# FUSION DES LISTES
# ============================================================================

def merge_unique_strings(
    old_items: Any,
    new_items: Any,
) -> List[str]:

    if not isinstance(
        old_items,
        list,
    ):
        old_items = []

    if not isinstance(
        new_items,
        list,
    ):
        new_items = []

    result = []
    seen = set()

    for item in (
        new_items
        + old_items
    ):

        cleaned = clean_item(
            item
        )

        if not cleaned:
            continue

        key = normalize(
            cleaned
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            cleaned
        )

    return result


def merge_source_ids(
    old_ids: Any,
    new_ids: Any,
) -> List[int]:

    if not isinstance(
        old_ids,
        list,
    ):
        old_ids = []

    if not isinstance(
        new_ids,
        list,
    ):
        new_ids = []

    result = []

    for value in (
        new_ids
        + old_ids
    ):

        try:
            value = int(value)
        except Exception:
            continue

        if value not in result:
            result.append(
                value
            )

    return sorted(
        result
    )


# ============================================================================
# FUSION STRUCTURÉE
# ============================================================================

def merge_structured_memories_local(
    old: Dict[str, Any],
    new: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "version": MEMORY_VERSION,

        "topic": (
            clean_item(
                new.get("topic")
            )
            or clean_item(
                old.get("topic")
            )
            or "Conversation"
        ),

        "type": (
            clean_item(
                new.get("type")
            )
            or clean_item(
                old.get("type")
            )
            or "other"
        ),

        "summary": merge_summaries_with_topic(
            old.get("summary", ""),
            new.get("summary", ""),
            clean_item(
                new.get("topic")
            )
            or clean_item(
                old.get("topic")
            ),
        ),

        "decisions": merge_unique_strings(
            old.get("decisions"),
            new.get("decisions"),
        ),

        "state": (
            clean_item(
                new.get("state")
            )
            or clean_item(
                old.get("state")
            )
        ),

        "facts": merge_unique_strings(
            old.get("facts"),
            new.get("facts"),
        ),

        "keywords": merge_unique_strings(
            old.get("keywords"),
            new.get("keywords"),
        ),

        "source_ids": merge_source_ids(
            old.get("source_ids"),
            new.get("source_ids"),
        ),

        "updated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
    }


# ============================================================================
# PROMPT CRÉATION
# ============================================================================

def build_synthesis_prompt(
    query: str,
    sources: List[Dict[str, Any]],
) -> str:

    formatted_sources = []

    for source in sources:

        formatted_sources.append(
            {
                "id": source.get("id"),
                "role": source.get("role"),
                "created_at": source.get("created_at"),
                "content": source.get(
                    "content",
                    "",
                ),
            }
        )

    return f"""
Tu es le système de mémoire long terme de Amah Agent.

Transforme les messages historiques en une mémoire synthétique
courte, précise et réutilisable.

REQUETE :
{query}

SOURCES :
{json.dumps(
    formatted_sources,
    ensure_ascii=False,
    indent=2,
)}

Retourne UNIQUEMENT :

{{
  "version": 2,
  "topic": "sujet précis",
  "type": "project|decision|discussion|fact|other",
  "summary": "résumé court et fidèle",
  "decisions": [],
  "state": "état actuel connu",
  "facts": [],
  "keywords": [],
  "source_ids": []
}}

Règles :
- ne rien inventer ;
- choisir un sujet précis ;
- conserver les informations importantes ;
- éviter les répétitions ;
- conserver les IDs des sources.
""".strip()


# ============================================================================
# PROMPT FUSION
# ============================================================================

def build_merge_prompt(
    query: str,
    previous_memory: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> str:

    formatted_sources = []

    for source in sources:

        formatted_sources.append(
            {
                "id": source.get("id"),
                "role": source.get("role"),
                "created_at": source.get("created_at"),
                "content": source.get(
                    "content",
                    "",
                ),
            }
        )

    return f"""
Tu es le système de mémoire long terme de Amah Agent.

Une mémoire existe déjà.
De nouvelles informations doivent être intégrées.

REQUETE :
{query}

MEMOIRE EXISTANTE :
{json.dumps(
    previous_memory,
    ensure_ascii=False,
    indent=2,
)}

NOUVELLES SOURCES :
{json.dumps(
    formatted_sources,
    ensure_ascii=False,
    indent=2,
)}

Retourne UNIQUEMENT :

{{
  "version": 2,
  "topic": "sujet précis",
  "type": "project|decision|discussion|fact|other",
  "summary": "résumé consolidé sans répétition",
  "decisions": [],
  "state": "état actuel",
  "facts": [],
  "keywords": [],
  "source_ids": []
}}

Règles :
- ne rien inventer ;
- conserver les anciennes informations toujours valables ;
- ajouter les nouvelles ;
- supprimer les doublons ;
- si une information change ou devient obsolète, privilégier la plus récente ;
- ne pas présenter simultanément l'ancienne et la nouvelle version d'un même fait comme si elles étaient toutes deux actuelles ;
- lorsqu'une nouvelle source corrige l'état précédent, remplacer l'ancienne formulation dans le résumé ;
- le résumé final doit éviter de répéter la même phrase ;
- conserver les sources ;
- conserver le sujet précis.
""".strip()


# ============================================================================
# PARSER
# ============================================================================

def parse_synthesis(
    raw: Any,
    source_ids: Optional[List[int]] = None,
    query: str = "",
) -> Optional[Dict[str, Any]]:

    if raw is None:
        return None

    if isinstance(raw, dict):
        data = dict(
            raw
        )

    else:

        text = str(
            raw
        ).strip()

        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        try:

            data = json.loads(
                text
            )

        except Exception:
            return None

    if not isinstance(data, dict):
        return None

    decisions = data.get(
        "decisions"
    ) or []

    facts = data.get(
        "facts"
    ) or []

    keywords = data.get(
        "keywords"
    ) or []

    if not isinstance(
        decisions,
        list,
    ):
        decisions = []

    if not isinstance(
        facts,
        list,
    ):
        facts = []

    if not isinstance(
        keywords,
        list,
    ):
        keywords = []

    return {
        "version": MEMORY_VERSION,

        "topic": (
            clean_item(
                data.get("topic")
            )
            or query
        ),

        "type": (
            clean_item(
                data.get("type")
            )
            or "other"
        ),

        "summary": clean_item(
            data.get("summary")
        ),

        "decisions": merge_unique_strings(
            [],
            decisions,
        ),

        "state": clean_item(
            data.get("state")
        ),

        "facts": merge_unique_strings(
            [],
            facts,
        ),

        "keywords": merge_unique_strings(
            [],
            keywords,
        ),

        "source_ids": merge_source_ids(
            [],
            (
                source_ids
                or data.get(
                    "source_ids"
                )
                or []
            ),
        ),

        "updated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
    }


# ============================================================================
# SAUVEGARDE
# ============================================================================

def save_structured_memory(
    memory: Dict[str, Any],
    previous_memory: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:

    content = json.dumps(
        memory,
        ensure_ascii=False,
    )

    if previous_memory:

        old_id = previous_memory.get(
            "_memory_id"
        )

        if old_id is not None:

            try:
                delete_memory(
                    int(old_id)
                )
            except Exception:
                pass

    try:

        return save_memory(
            content,
            SUMMARY_CATEGORY,
        )

    except TypeError:

        try:

            return save_memory(
                content=content,
                category=SUMMARY_CATEGORY,
            )

        except Exception:
            return None

    except Exception:
        return None


# ============================================================================
# FUSION
# ============================================================================

def merge_memory(
    query: str,
    previous_memory: Dict[str, Any],
    sources: List[Dict[str, Any]],
    summarize_fn: Optional[
        Callable[[str], Any]
    ] = None,
) -> Tuple[
    Optional[Dict[str, Any]],
    bool,
]:

    source_ids = get_source_ids(
        sources
    )

    # ------------------------------------------------------------
    # Fusion locale.
    # ------------------------------------------------------------

    if summarize_fn is None:

        incoming = {
            "version": MEMORY_VERSION,

            "topic": (
                previous_memory.get(
                    "topic"
                )
                or query
            ),

            "type": previous_memory.get(
                "type",
                "other",
            ),

            "summary": "",

            "decisions": [],

            "state": "",

            "facts": [],

            "keywords": [],

            "source_ids": source_ids,
        }

        merged = merge_structured_memories_local(
            previous_memory,
            incoming,
        )

        return merged, False

    # ------------------------------------------------------------
    # Fusion LLM.
    # ------------------------------------------------------------

    prompt = build_merge_prompt(
        query=query,
        previous_memory=previous_memory,
        sources=sources,
    )

    try:

        raw = summarize_fn(
            prompt
        )

    except Exception:

        return None, False

    merged = parse_synthesis(
        raw=raw,
        source_ids=source_ids,
        query=query,
    )

    if not merged:
        return None, False

    # Sécurité : fusion locale finale.
    merged = merge_structured_memories_local(
        previous_memory,
        merged,
    )

    return merged, True


# ============================================================================
# RECALL
# ============================================================================

def recall(
    query: str,
    summarize_fn: Optional[
        Callable[[str], Any]
    ] = None,
    limit: int = DEFAULT_SOURCE_LIMIT,
) -> Dict[str, Any]:

    query = str(
        query or ""
    ).strip()

    if not query:

        return {
            "mode": "empty",
            "query": query,
            "sources": [],
        }

    # ============================================================
    # EXACT
    # ============================================================

    if wants_exact_sources(query):

        sources = find_sources(
            query,
            limit,
        )

        return {
            "mode": "exact",
            "query": query,
            "sources": sources,
            "cached": False,
        }

    # ============================================================
    # MÉMOIRE EXISTANTE
    # ============================================================

    previous_memory = find_best_memory(
        query
    )

    # ============================================================
    # SOURCES
    # ============================================================

    sources = find_sources(
        query,
        limit,
    )

    # ============================================================
    # AUCUNE SOURCE
    # ============================================================

    if not sources:

        if previous_memory:

            return {
                **previous_memory,
                "mode": "summary_cached",
                "query": query,
                "cached": True,
                "sources": [],
                "memory_saved": False,
                "used_llm": False,
            }

        return {
            "mode": "not_found",
            "query": query,
            "sources": [],
            "cached": False,
            "memory_saved": False,
            "message": (
                "Aucune information historique "
                "suffisamment pertinente n'a été trouvée."
            ),
        }

    # ============================================================
    # MÉMOIRE EXISTANTE
    # ============================================================

    if previous_memory:

        # --------------------------------------------------------
        # Aucune source nouvelle.
        # --------------------------------------------------------

        if not has_new_sources(
            previous_memory,
            sources,
        ):

            return {
                **previous_memory,
                "mode": "summary_cached",
                "query": query,
                "cached": True,
                "sources": [],
                "memory_saved": False,
                "used_llm": False,
            }

        # --------------------------------------------------------
        # Nouvelle information.
        # --------------------------------------------------------

        merged, used_llm = merge_memory(
            query=query,
            previous_memory=previous_memory,
            sources=sources,
            summarize_fn=summarize_fn,
        )

        if merged:

            memory_id = save_structured_memory(
                merged,
                previous_memory,
            )

            merged["_memory_id"] = (
                memory_id
            )

            return {
                **merged,
                "mode": "summary_updated",
                "query": query,
                "cached": False,
                "sources": sources,
                "memory_saved": (
                    memory_id is not None
                ),
                "used_llm": used_llm,
            }

    # ============================================================
    # NOUVELLE MÉMOIRE
    # ============================================================

    prompt = build_synthesis_prompt(
        query,
        sources,
    )

    if summarize_fn is None:

        return {
            "mode": "summary_needed",
            "query": query,
            "sources": sources,
            "prompt": prompt,
            "summary": None,
            "memory_saved": False,
            "cached": False,
            "used_llm": False,
        }

    try:

        raw = summarize_fn(
            prompt
        )

    except Exception as exc:

        return {
            "mode": "summary_error",
            "query": query,
            "sources": sources,
            "prompt": prompt,
            "summary": None,
            "memory_saved": False,
            "cached": False,
            "used_llm": True,
            "error": str(exc),
        }

    structured = parse_synthesis(
        raw=raw,
        source_ids=get_source_ids(
            sources
        ),
        query=query,
    )

    if structured is None:

        return {
            "mode": "summary_parse_error",
            "query": query,
            "sources": sources,
            "prompt": prompt,
            "summary": None,
            "memory_saved": False,
            "cached": False,
            "used_llm": True,
        }

    memory_id = save_structured_memory(
        structured
    )

    structured["_memory_id"] = (
        memory_id
    )

    return {
        **structured,
        "mode": "summary",
        "query": query,
        "sources": sources,
        "prompt": prompt,
        "summary": structured.get(
            "summary"
        ),
        "memory_saved": (
            memory_id is not None
        ),
        "cached": False,
        "used_llm": True,
    }


# ============================================================================
# FORMATAGE
# ============================================================================

def format_recall(
    result: Dict[str, Any],
) -> str:

    mode = result.get(
        "mode"
    )

    if mode == "exact":

        sources = result.get(
            "sources",
            [],
        )

        if not sources:

            return (
                "Je n'ai pas retrouvé "
                "les messages demandés."
            )

        blocks = []

        for source in sources:

            blocks.append(
                f"[{source.get('role')} "
                f"#{source.get('id')}]\n"
                f"{source.get('content', '')}"
            )

        return "\n\n".join(
            blocks
        )

    if mode in {
        "summary",
        "summary_cached",
        "summary_updated",
    }:

        topic = (
            result.get("topic")
            or "Sujet"
        )

        summary = (
            result.get("summary")
            or ""
        )

        lines = [
            f"{topic} :",
            summary,
        ]

        state = result.get(
            "state"
        )

        if state:
            lines.append(
                f"État actuel : {state}"
            )

        decisions = (
            result.get("decisions")
            or []
        )

        if decisions:

            lines.append(
                "Décisions : "
                + "; ".join(
                    decisions
                )
            )

        return "\n".join(
            lines
        )

    if mode == "summary_needed":

        return (
            "J'ai retrouvé des éléments "
            "pertinents, mais ils doivent "
            "encore être synthétisés."
        )

    if mode == "not_found":

        return str(
            result.get("message")
            or "Aucune mémoire pertinente trouvée."
        )

    if mode in {
        "summary_error",
        "summary_parse_error",
    }:

        return (
            "Les informations ont été retrouvées, "
            "mais la mémoire n'a pas pu être mise "
            "à jour."
        )

    return ""