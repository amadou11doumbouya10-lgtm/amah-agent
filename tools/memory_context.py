"""Rappel de mémoire (Memory Recall V0.2.4) partagé par agent.py et gui.py.

Déplacé depuis agent.py pour que l'interface clients en profite : sur une
demande du type "tu te souviens de ce qu'on avait dit sur…", Amah retrouve les
échanges passés (table conversations) et en donne un résumé sourcé.

- Demande mémoire pure : réponse directe (format_recall), sans LLM conversationnel.
- Demande mémoire + action : la mémoire trouvée est injectée dans le prompt
  système pour l'appel normal, sans appel LLM supplémentaire.
"""
from __future__ import annotations

import re
from time import perf_counter
from typing import Callable, Optional, Tuple

from tools.memory_recall_v024 import (
    recall,
    format_recall,
    wants_exact_sources,
    find_best_memory,
    find_sources,
)
from tools.router_v03 import detect_intents

MEMORY_QUERY_PATTERNS = [
    r"\bqu est ce qu on avait dit\b",
    r"\bqu est ce qu on avait decide\b",
    r"\bce qu on avait dit\b",
    r"\bce qu on avait decide\b",
    r"\btu te souviens\b",
    r"\bte souviens tu\b",
    r"\bnotre conversation\b",
    r"\bhistorique\b",
    r"\bla derniere fois\b",
    r"\bqu on a fait\b",
    r"\bqu on a decide\b",
    r"\brappelle moi\b.*\b(projet|conversation|decide|dit|memoire|historique)\b",
]

_ACTION_VERBS = (
    "donne|dis|dit|indique|montre|ouvre|lance|cherche|fais|calcule|affiche|va|envoie|execute|exécute"
)

# Résultats qui répondent directement à la demande, sans appel LLM
DIRECT_MODES = {"exact", "summary", "summary_cached", "summary_updated"}


def normalize_for_matching(text: str) -> str:
    text = str(text or "").lower().strip()
    for old, new in {
        "é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a", "ä": "a",
        "î": "i", "ï": "i", "ô": "o", "ö": "o", "ù": "u", "û": "u", "ü": "u", "ç": "c",
    }.items():
        text = text.replace(old, new)
    text = text.replace("'", " ").replace("’", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_memory_query(user_text: str) -> bool:
    text = normalize_for_matching(user_text)
    if not text:
        return False
    if wants_exact_sources(user_text):
        return True
    return any(re.search(pattern, text) for pattern in MEMORY_QUERY_PATTERNS)


def has_non_memory_intent(user_text: str) -> bool:
    try:
        intents = detect_intents(user_text)
    except Exception:
        return False
    ignored = {"memory_read", "memory_save", "fallback_all_tools", "safe_fallback"}
    return any(intent not in ignored for intent in intents)


def extract_memory_query(user_text: str) -> str:
    """Partie mémoire d'une demande mixte ("… puis ouvre X" -> "…")."""
    text = str(user_text or "").strip()
    if not text:
        return text
    for joiner in ("puis", "ensuite", "et", "après"):
        # (Le motif d'origine "\s+ puis \s+" exigeait deux espaces autour du mot
        # et ne correspondait jamais à une phrase normale.)
        match = re.search(rf"\s+{joiner}\s+(?=(?:{_ACTION_VERBS})\b)", text, flags=re.IGNORECASE)
        if match:
            prefix = text[:match.start()].strip(" ,;:.")
            if prefix:
                return prefix
    return text


def extract_memory_subject(user_text: str) -> str:
    normalized = normalize_for_matching(extract_memory_query(user_text))
    if not normalized:
        return ""
    for pattern in (r"\bsur\s+(.+)$", r"\bpour\s+(.+)$", r"\bconcernant\s+(.+)$", r"\ba propos de\s+(.+)$"):
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            subject = match.group(1).strip(" .,:;!?\n\r")
            if subject:
                return subject
    return ""


def cached_memory_for_mixed_query(user_text: str) -> Optional[dict]:
    """Cherche une mémoire déjà résumée, sans LLM (sujet d'abord)."""
    candidates = [extract_memory_subject(user_text), extract_memory_query(user_text), user_text]
    seen = set()
    for candidate in candidates:
        key = normalize_for_matching(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            cached = find_best_memory(candidate)
        except Exception:
            cached = None
        if cached:
            return {
                **cached,
                "mode": "summary_cached",
                "query": user_text,
                "cached": True,
                "sources": [],
                "memory_saved": False,
                "used_llm": False,
            }
    return None


def sources_memory_for_mixed_query(memory_query: str) -> Optional[dict]:
    """Sans mémoire résumée : sources historiques brutes, données au LLM final."""
    if not memory_query:
        return None
    try:
        sources = find_sources(memory_query, limit=6)
    except Exception:
        return None
    if not sources:
        return None
    return {
        "mode": "history_sources",
        "query": memory_query,
        "cached": False,
        "sources": sources,
        "memory_saved": False,
        "used_llm": False,
    }


def memory_context(
    user_text: str,
    summarize_fn: Callable[[str], str],
    log: Optional[Callable[[str], None]] = None,
) -> Tuple[Optional[dict], bool]:
    """Retourne (résultat mémoire, réponse_directe).

    summarize_fn(prompt) -> texte JSON : appel LLM de synthèse, sans outil.
    log(message) : diagnostic facultatif.
    """
    if not is_memory_query(user_text):
        return None, False

    started = perf_counter()
    elapsed = lambda: (perf_counter() - started) * 1000
    note = log or (lambda message: None)

    if has_non_memory_intent(user_text):
        cached = cached_memory_for_mixed_query(user_text)
        if cached:
            note(f"[MEMORY] mode=summary_cached | cache=True | llm=False | mixed=True | {elapsed():.1f} ms")
            return cached, False
        history_sources = sources_memory_for_mixed_query(extract_memory_query(user_text))
        if history_sources:
            history_sources["mixed"] = True
            note(f"[MEMORY] mode=history_sources | cache=False | llm=False | mixed=True | {elapsed():.1f} ms")
            return history_sources, False
        note(f"[MEMORY] mixed=True | cache=False | llm=False | history_not_found | {elapsed():.1f} ms")
        return None, False

    result = recall(query=user_text, summarize_fn=summarize_fn, limit=6)
    mode = result.get("mode", "unknown")
    note(
        f"[MEMORY] mode={mode} | cache={result.get('cached', False)} "
        f"| llm={result.get('used_llm', False)} | {elapsed():.1f} ms"
    )
    return result, mode in DIRECT_MODES


def format_history_sources(result: dict) -> str:
    blocks = []
    for source in result.get("sources", []) or []:
        content = str(source.get("content", "") or "").strip()
        if content:
            blocks.append(f"[Source #{source.get('id')} | {source.get('role', 'unknown')}]\n{content}")
    return "\n\n".join(blocks)


def memory_instruction(result: dict) -> str:
    """Bloc à ajouter temporairement au prompt système (demande mixte)."""
    if not result:
        return ""
    if result.get("mode", "") == "history_sources":
        formatted = format_history_sources(result)
    else:
        formatted = format_recall(result)
    if not formatted:
        return ""
    return (
        "\n\n"
        "[MEMOIRE PERTINENTE — Memory Recall V0.2.4]\n"
        "Les éléments ci-dessous proviennent de l'historique. "
        "Utilise-les uniquement comme contexte historique. "
        "Ne prétends pas qu'ils proviennent de la conversation courante.\n\n"
        + formatted
    )


SUMMARY_SYSTEM = (
    "Tu es le module de synthèse mémoire de Amah Agent. "
    "Retourne uniquement le JSON demandé par le prompt."
)

__all__ = [
    "memory_context", "memory_instruction", "format_recall", "is_memory_query",
    "normalize_for_matching", "SUMMARY_SYSTEM",
]
