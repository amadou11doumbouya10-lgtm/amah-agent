"""Réponses instantanées sans appel LLM (heure, date, calcul simple).

Partagé par agent.py et gui.py : "quelle heure est-il ?" ou "calcule 17*23"
répondent en quelques millisecondes et ne consomment aucun quota Groq.
"""
from __future__ import annotations

import re
from typing import Optional

from tools.router_v04 import normalize_for_router
from tools.fastpath_v01 import normalize_text, _extract_calculation


def datetime_request_kind(user_text: str) -> Optional[str]:
    """Demande évidente de date/heure : "time", "date", "datetime" ou None.

    Accepte quelques fautes fréquentes ("kel heur"). Une durée ou une date
    relative ("dans 45 jours", "à 8 heures") n'en est pas une : add_days,
    set_reminder ou create_daily_task doivent passer par le routeur.
    """
    text = normalize_for_router(user_text)
    if not text:
        return None
    if re.search(
        r"\b(?:dans|il y a|depuis|pendant)\s+\d+"
        r"|\b\d+\s*(?:jours?|semaines?|mois|ans|annees?|heures?|h|minutes?|min)\b",
        text,
    ):
        return None

    time_patterns = [
        r"\bquel(?:le)? heure\b",
        r"^heures?$",
        r"\b(?:donne|dis)(?: moi)? l heure\b",
        r"\bheure actuelle\b",
        r"\bil fait quelle heure\b",
        r"\bca fait quelle heure\b",
        r"\bheure est il\b",
    ]
    date_patterns = [
        r"\bquel(?:le)? date\b",
        r"\bquel jour\b",
        r"\bdate d aujourd hui\b",
        r"\bdate aujourd hui\b",
        r"\bdate actuelle\b",
        r"\bquel(?:le)? est la date\b",
    ]
    asks_time = any(re.search(p, text) for p in time_patterns)
    asks_date = any(re.search(p, text) for p in date_patterns)
    if asks_time and asks_date:
        return "datetime"
    if asks_time:
        return "time"
    if asks_date:
        return "date"
    return None


def format_datetime(kind: Optional[str], data: dict) -> str:
    date_value = data.get("date")
    time_value = data.get("heure") or data.get("time")
    if kind == "time" and time_value:
        return f"Il est {time_value}."
    if kind == "date" and date_value:
        jour = data.get("jour")
        return f"Nous sommes le {jour.lower() + ' ' if jour else ''}{date_value}."
    if date_value and time_value:
        return f"Il est {time_value}, le {date_value}."
    return f"Il est {time_value}." if time_value else f"Nous sommes le {date_value}."


def instant_reply(user_text: str) -> Optional[str]:
    """Réponse locale pour l'heure, la date ou un calcul simple, sinon None."""
    from tools import TOOL_FUNCTIONS

    kind = datetime_request_kind(user_text)
    if kind:
        data = TOOL_FUNCTIONS["get_datetime"]()
        if isinstance(data, dict) and not data.get("error"):
            return format_datetime(kind, data)

    expression = _extract_calculation(normalize_text(user_text))
    if expression:
        data = TOOL_FUNCTIONS["calculate"](expression=expression)
        if isinstance(data, dict) and data.get("success"):
            value = data.get("resultat")
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            return f"{expression} = {value}"
    return None
