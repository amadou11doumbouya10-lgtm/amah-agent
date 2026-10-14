\
"""
Amah Agent — Router V0.4

Couche de compatibilité au-dessus de Router V0.3.

Objectif : conserver les intentions et la sélection d'outils de V0.3,
mais mieux tolérer les fautes simples et les formulations de type SMS.

Principe :
    1. Router V0.3 sur le texte normalisé.
    2. Si rien n'est reconnu, correction lexicale légère/fuzzy.
    3. Router V0.3 sur la version corrigée.
    4. Sinon, même fallback que V0.3.

Aucun appel LLM.
Compatible Python 3.9.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, Set, Tuple

from tools.router_v03 import (
    route_tools as _route_tools_v03,
    is_simple_chat as _is_simple_chat_v03,
)


# ---------------------------------------------------------------------------
# CORRECTIONS COURANTES DE TYPE SMS / ORTHOGRAPHE
# ---------------------------------------------------------------------------

COMMON_REPLACEMENTS: Dict[str, str] = {
    # Heure / date
    "heur": "heure",
    "heurs": "heures",
    "heurre": "heure",
    "heures": "heures",
    "lheur": "l heure",
    "leur": "heure",
    "leure": "heure",
    "eur": "heure",

    # Question / formulation
    "kel": "quel",
    "kelle": "quelle",
    "qu elle": "quelle",
    "koi": "quoi",
    "kes": "qu est",
    "kesk": "qu est ce",
    "keske": "qu est ce",
    "c koi": "c est quoi",
    "mwa": "moi",
    "toi": "toi",

    # Verbes fréquents
    "fai": "fais",
    "fé": "fais",
    "fer": "faire",
    "di": "dis",
    "dit": "dit",
    "donne moi": "donne moi",
    "peu": "peux",
    "pe": "peux",
    "vou": "veux",
    "veu": "veux",
    "cherch": "cherche",
    "trouv": "trouve",
    "ouvr": "ouvre",
    "lanc": "lance",
    "instal": "installe",
    "telecharg": "télécharge",

    # Petites variantes déjà vues dans le projet
    "ecran": "écran",
    "sa": "ça",
}


# Tokens très courts ou ambigus à ne jamais corriger automatiquement.
NEVER_FUZZY = {
    "a", "ai", "au", "ce", "c", "de", "du", "en", "et", "il", "la",
    "le", "les", "ma", "me", "mon", "ne", "ni", "on", "ou", "par",
    "pas", "pe", "pour", "que", "qui", "sa", "se", "si", "son", "sur",
    "ta", "te", "tes", "un", "une", "va", "vers", "je", "tu", "nous",
    "vous", "y", "l",
}


# ---------------------------------------------------------------------------
# NORMALISATION
# ---------------------------------------------------------------------------


def _strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    return "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )


def normalize_basic(text: str) -> str:
    text = str(text or "").lower().strip()
    text = _strip_accents(text)
    text = text.replace("'", " ")
    text = text.replace("’", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _apply_phrase_replacements(text: str) -> str:
    # Plus longs d'abord pour éviter qu'un sous-fragment casse une expression.
    for old, new in sorted(COMMON_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = rf"(?<![a-z0-9]){re.escape(normalize_basic(old))}(?![a-z0-9])"
        text = re.sub(pattern, new, text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# LEXIQUE FUZZY : construit dynamiquement depuis Router V0.3
# ---------------------------------------------------------------------------


def _walk_strings(value: Any, seen=None) -> Iterable[str]:
    if seen is None:
        seen = set()

    value_id = id(value)
    if value_id in seen:
        return
    seen.add(value_id)

    if isinstance(value, str):
        yield value
        return

    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(key, seen)
            yield from _walk_strings(item, seen)
        return

    if isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _walk_strings(item, seen)


def _build_router_lexicon() -> Set[str]:
    try:
        import tools.router_v03 as router_module
    except Exception:
        return set()

    lexicon: Set[str] = set()

    for name, value in vars(router_module).items():
        if name.startswith("__"):
            continue

        for raw in _walk_strings(value):
            normalized = normalize_basic(raw)
            for token in normalized.split():
                if len(token) >= 4 and token.isalpha():
                    lexicon.add(token)

    return lexicon


_ROUTER_LEXICON = _build_router_lexicon()


def _fuzzy_threshold(token: str) -> float:
    length = len(token)
    if length <= 4:
        return 0.90
    if length <= 6:
        return 0.84
    return 0.80


def _best_fuzzy_token(token: str) -> str:
    if len(token) < 4 or token in NEVER_FUZZY:
        return token

    if token in _ROUTER_LEXICON:
        return token

    # Évite des corrections absurdes trop éloignées en longueur.
    candidates = [
        item
        for item in _ROUTER_LEXICON
        if abs(len(item) - len(token)) <= 2
    ]

    if not candidates:
        return token

    best = token
    best_score = 0.0

    for candidate in candidates:
        score = SequenceMatcher(None, token, candidate).ratio()
        if score > best_score:
            best = candidate
            best_score = score

    if best_score >= _fuzzy_threshold(token):
        return best

    return token


def _apply_fuzzy_tokens(text: str) -> str:
    tokens = text.split()
    corrected = [_best_fuzzy_token(token) for token in tokens]
    return " ".join(corrected)


# ---------------------------------------------------------------------------
# API ROUTER V0.4
# ---------------------------------------------------------------------------


def normalize_for_router(text: str) -> str:
    """Normalise et corrige légèrement une demande utilisateur."""
    normalized = normalize_basic(text)
    normalized = _apply_phrase_replacements(normalized)
    return _apply_fuzzy_tokens(normalized)


def route_tools(
    user_text: str,
    tools_definitions: list,
    max_tools: int = 12,
) -> Tuple[list, list]:
    """
    Compatibilité V0.3 + correction fuzzy uniquement si V0.3 ne reconnaît rien.
    """
    original = str(user_text or "")
    normalized = normalize_for_router(original)

    selected, intents = _route_tools_v03(
        normalized,
        tools_definitions,
        max_tools=max_tools,
    )

    # Le routage initial a fonctionné : aucun fuzzy supplémentaire.
    if selected:
        return selected, intents

    # Recherche documentaire générale, absente des patterns V0.3.
    research_patterns = (
        r"\bcherche(?:[- ]moi)? toutes? les informations (?:importantes )?sur\b",
        r"\brecherche(?:[- ]moi)? toutes? les informations (?:importantes )?sur\b",
        r"\bcherche(?:[- ]moi)? des informations sur\b",
        r"\brecherche(?:[- ]moi)? des informations sur\b",
        r"\btrouve(?:[- ]moi)? des informations sur\b",
        r"\bdonne(?:[- ]moi)? les informations importantes sur\b",
        r"\brenseigne(?:[- ]moi)? sur\b",
    )
    if any(re.search(pattern, normalized) for pattern in research_patterns):
        tool_by_name = {
            str(item.get("function", {}).get("name", "")): item
            for item in tools_definitions
            if isinstance(item, dict)
        }
        selected = [
            tool_by_name[name]
            for name in ("web_search", "read_webpage")
            if name in tool_by_name
        ]
        if selected:
            return selected[:max_tools], ["web_search"]

    # Même pour la conversation simple, laisser V0.3 décider.
    if _is_simple_chat_v03(normalized):
        return selected, intents

    # Second essai avec corrections plus agressives, sur la base du lexique V0.3.
    fuzzy_text = _apply_fuzzy_tokens(normalized)

    if fuzzy_text != normalized:
        selected, intents = _route_tools_v03(
            fuzzy_text,
            tools_definitions,
            max_tools=max_tools,
        )

    return selected, intents


def is_simple_chat(user_text: str) -> bool:
    """Version V0.4 de la détection de conversation simple."""
    normalized = normalize_for_router(user_text)
    return _is_simple_chat_v03(normalized)


__all__ = [
    "COMMON_REPLACEMENTS",
    "normalize_basic",
    "normalize_for_router",
    "route_tools",
    "is_simple_chat",
]
