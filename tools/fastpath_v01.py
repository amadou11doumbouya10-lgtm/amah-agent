"""
Amah Agent — FastPath V1.4

Détection locale des commandes simples qui peuvent être exécutées sans appel LLM.

V1 couvre volontairement peu de cas, mais avec une contrainte forte :
NE PAS déclencher d'action si l'intention ou les paramètres ne sont pas assez clairs.

Cas V1 :
- capture d'écran -> screenshot_full / take_screenshot
- calcul arithmétique simple -> calculate
- "cherche sur Google" sans terme -> réponse locale demandant le terme
- recherche Google avec requête -> web_search direct sans LLM

Compatible Python 3.9.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Optional
import inspect


_SCREENSHOT_PATTERNS = [
    r"\bfais(?: moi)? une capture(?: de| d)?(?: mon)? ecran\b",
    r"\bfaire une capture(?: de| d)?(?: mon)? ecran\b",
    r"\bprends(?: moi)? une capture(?: de| d)?(?: mon)? ecran\b",
    r"\bprendre une capture(?: de| d)?(?: mon)? ecran\b",
    r"\bscreenshot\b",
]

_SEARCH_GOOGLE_PATTERNS = [
    r"\bcherche sur google\b",
    r"\brecherche sur google\b",
    r"\bcherche google\b",
    r"\brecherche google\b",
]

_SEARCH_QUERY_PATTERNS = [
    r"^cherche(?: sur)? google\s+(.+)$",
    r"^recherche(?: sur)? google\s+(.+)$",
    r"^cherche(?: sur)? internet\s+(.+)$",
    r"^recherche(?: sur)? internet\s+(.+)$",
    r"^cherche(?: sur)? le web\s+(.+)$",
    r"^recherche(?: sur)? le web\s+(.+)$",
]

_RESEARCH_QUERY_PATTERNS = [
    r"^cherche(?:[- ]moi)? toutes? les informations (?:importantes )?sur (.+)$",
    r"^recherche(?:[- ]moi)? toutes? les informations (?:importantes )?sur (.+)$",
    r"^cherche(?:[- ]moi)? des informations sur (.+)$",
    r"^recherche(?:[- ]moi)? des informations sur (.+)$",
    r"^trouve(?:[- ]moi)? des informations sur (.+)$",
    r"^donne(?:[- ]moi)? les informations importantes sur (.+)$",
    r"^renseigne(?:[- ]moi)? sur (.+)$",
]

_CALCULATION_PREFIXES = [
    r"^calcule(?:[- ]moi)?(?:[- ]le)?\s+",
    r"^calcul\s+",
    r"^combien fait\s+",
    r"^fais le calcul de\s+",
]

_MATH_ALLOWED = re.compile(r"^[0-9\s+\-*/().,%xX×÷]+$")


def _strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    return "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )


def normalize_text(text: str) -> str:
    text = str(text or "").lower().strip()
    text = text.replace("’", "'")
    text = _strip_accents(text)
    text = text.replace("'", " ")
    text = re.sub(r"[^a-z0-9%+\-*/().,\s×÷xX]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _has_question_mode(text: str) -> bool:
    # "comment faire une capture" n'est pas une commande d'exécution.
    return bool(
        re.search(
            r"\bcomment\b|\bcomment faire\b|\bcomment prendre\b|\bqu est ce que\b",
            text,
        )
    )


def _find_tool(tool_functions: Any, candidates) -> Optional[str]:
    for name in candidates:
        if isinstance(tool_functions, dict) and callable(tool_functions.get(name)):
            return name
    return None


def _desktop_screenshot_path() -> str:
    desktop = Path.home() / "Desktop"
    try:
        desktop.mkdir(parents=True, exist_ok=True)
    except Exception:
        desktop = Path.home()

    base = desktop / "screenshot_fastpath.png"
    if not base.exists():
        return str(base)

    for index in range(2, 1000):
        candidate = desktop / f"screenshot_fastpath_{index}.png"
        if not candidate.exists():
            return str(candidate)

    return str(desktop / "screenshot_fastpath_latest.png")


def _screenshot_args(func: Any) -> Dict[str, Any]:
    """Construit les arguments sans supposer une signature exacte."""
    try:
        parameters = inspect.signature(func).parameters
    except Exception:
        return {}

    path = _desktop_screenshot_path()

    for key in ("path", "file_path", "output_path", "save_path"):
        if key in parameters:
            return {key: path}

    return {}


def _extract_calculation(text: str) -> Optional[str]:
    for pattern in _CALCULATION_PREFIXES:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        expression = text[match.end():].strip()
        if not expression:
            return None

        # Normalise les opérateurs écrits en langage courant.
        expression = expression.replace("×", "*")
        expression = expression.replace("÷", "/")
        expression = re.sub(r"(?<=\d)\s*[xX]\s*(?=\d)", "*", expression)
        expression = expression.replace(",", ".")
        expression = re.sub(r"\s+", " ", expression).strip()

        if not _MATH_ALLOWED.fullmatch(expression):
            return None

        # Pour V1, on refuse une expression ambiguë ou vide.
        if not re.search(r"\d", expression):
            return None

        return expression

    return None


def _google_missing_query(text: str) -> bool:
    return any(
        re.search(pattern, text)
        for pattern in _SEARCH_GOOGLE_PATTERNS
    ) and not re.search(r"\b(?:sur google|google)\b\s+\S+", text)


def _clean_search_query(query: str) -> str:
    query = re.sub(r"\s+", " ", str(query or "")).strip()
    # La normalisation supprime l'apostrophe de "l'iPhone".
    query = re.sub(r"^l\s+(?=iphone\b)", "", query, flags=re.IGNORECASE)
    query = query.rstrip(" .!?;:")
    return query.strip()


def _extract_search_query(text: str) -> Optional[str]:
    for pattern in (_SEARCH_QUERY_PATTERNS + _RESEARCH_QUERY_PATTERNS):
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        query = _clean_search_query(match.group(1))
        if query and query not in {"google", "internet", "le web", "web"}:
            return query
    return None


_BROWSER_INCOMPLETE_PATTERNS = (
    r"^ouvre(?: le| un| la)? html$",
    r"^ouvre(?: vision ama| vision a ma)$",
    r"^ouvre$",
)


def _browser_missing_target_reply(text: str) -> Optional[str]:
    for pattern in _BROWSER_INCOMPLETE_PATTERNS:
        if re.match(pattern, text, flags=re.IGNORECASE):
            if text == "ouvre":
                return "Que souhaites-tu que j'ouvre ? Donne-moi une URL, un fichier ou un dossier."
            return "Quel fichier HTML, quelle URL ou quel élément souhaites-tu que j'ouvre ?"
    return None

def detect_fastpath(
    user_text: str,
    tool_functions: Any,
    context: Any = None,
) -> Optional[Dict[str, Any]]:
    """
    Retourne une action FastPath ou None.

    Format :
      {"kind": "tool", "tool_name": ..., "args": {...}}
      {"kind": "reply", "response": ...}
    """
    text = normalize_text(user_text)
    if not text:
        return None

    for pattern in _RESEARCH_QUERY_PATTERNS:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            query = _clean_search_query(match.group(1))
            if query and _find_tool(tool_functions, ("web_search",)):
                return {
                    "kind": "tool",
                    "tool_name": "web_search",
                    "args": {"query": query, "num_results": 5},
                    "label": "recherche documentaire directe",
                }
            break

    if _has_question_mode(text):
        return None

    missing_target = _browser_missing_target_reply(text)
    if missing_target:
        return {
            "kind": "reply",
            "response": missing_target,
            "label": "cible navigateur manquante",
        }

    # ------------------------------------------------------------------
    # Capture d'écran
    # ------------------------------------------------------------------
    if any(re.search(pattern, text) for pattern in _SCREENSHOT_PATTERNS):
        tool_name = _find_tool(
            tool_functions,
            ("screenshot_full", "take_screenshot"),
        )
        if tool_name:
            func = tool_functions[tool_name]
            return {
                "kind": "tool",
                "tool_name": tool_name,
                "args": _screenshot_args(func),
                "label": "capture d'écran",
            }

    # ------------------------------------------------------------------
    # Calcul arithmétique simple
    # ------------------------------------------------------------------
    expression = _extract_calculation(text)
    if expression and _find_tool(tool_functions, ("calculate",)):
        return {
            "kind": "tool",
            "tool_name": "calculate",
            "args": {"expression": expression},
            "label": "calcul",
        }

    # ------------------------------------------------------------------
    # Recherche web directe : extraction locale de la requête.
    # ------------------------------------------------------------------
    search_query = _extract_search_query(text)
    if search_query and _find_tool(tool_functions, ("web_search",)):
        return {
            "kind": "tool",
            "tool_name": "web_search",
            "args": {
                "query": search_query,
                "num_results": 5,
            },
            "label": "recherche web directe",
        }

    # ------------------------------------------------------------------
    # Google sans requête : aucune raison de lancer le LLM.
    # ------------------------------------------------------------------
    if _google_missing_query(text):
        return {
            "kind": "reply",
            "response": "Que veux-tu que je recherche sur Google ?",
            "label": "recherche Google sans terme",
        }

    return None
