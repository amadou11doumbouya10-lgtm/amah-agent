"""Amah Agent — Planner / Reasoner V0.6 (recherche approfondie)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, List, Optional

from tools.planner_v04 import PlannerPlan, PlannerStep


def _norm(text: str) -> str:
    text = str(text or "").lower().strip()
    table = str.maketrans({
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a", "î": "i", "ï": "i",
        "ô": "o", "ö": "o", "ù": "u", "û": "u", "ü": "u", "ç": "c",
    })
    return re.sub(r"\s+", " ", text.translate(table))


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t.,;:!?\"'")


def _extract_subject(user_text: str, context: Any = None) -> str:
    pattern = (
        r"\b(?:iphone|ipad|macbook|pixel|galaxy)\s*"
        r"(?:\d{1,2}(?:\s+(?:pro|max|air|plus))?|[A-Za-z0-9-]+)\b"
    )
    matches = re.findall(pattern, str(user_text or ""), flags=re.IGNORECASE)
    if matches:
        return _clean(matches[-1])

    topic = _clean(getattr(context, "topic", "") or "") if context is not None else ""
    topic_match = re.search(
        r"\b(?:iphone|ipad|macbook|pixel|galaxy)\b[^,.!?]{0,40}",
        topic,
        flags=re.IGNORECASE,
    )
    if topic_match:
        return _clean(topic_match.group(0))
    return ""


def is_deep_research_request(user_text: str) -> bool:
    n = _norm(user_text)
    if not n:
        return False
    triggers = (
        "toutes les informations",
        "toutes les info",
        "informations importantes",
        "tout sur ",
        "tout ce qu il faut savoir",
        "tous les details",
        "toutes les caracteristiques",
        "caracteristiques completes",
        "dossier sur ",
        "analyse complete",
        "analyse approfondie",
        "etude complete",
        "renseigne moi sur ",
        "fais moi un dossier",
    )
    return any(trigger in n for trigger in triggers)


def _has_market_in_current_request(user_text: str) -> bool:
    n = _norm(user_text)
    return any(token in n for token in ("guinee", "guinea", "conakry", "gnf"))


def _build_steps(subject: str, user_text: str) -> List[PlannerStep]:
    market = " Guinée Conakry" if _has_market_in_current_request(user_text) else ""
    queries = [
        (
            "search_specs",
            f"{subject} Apple officiel caractéristiques écran design processeur stockage",
            "vérifier les caractéristiques de base et les données officielles",
        ),
        (
            "search_camera_battery",
            f"{subject} caméra autonomie batterie recharge performances tests",
            "recueillir les informations sur caméra, autonomie, recharge et performances",
        ),
        (
            "search_sim",
            f"{subject} SIM physique eSIM nano SIM connectivité variantes pays",
            "vérifier les variantes SIM/eSIM et les différences régionales",
        ),
        (
            "search_price",
            f"{subject} prix disponibilité 2026{market} Apple revendeurs",
            "chercher le prix et la disponibilité sur des sources commerciales ou officielles",
        ),
    ]
    return [
        PlannerStep(
            step_id=step_id,
            action="search",
            tool_name="web_search",
            args={"query": _clean(query), "num_results": 5},
            purpose=purpose,
        )
        for step_id, query, purpose in queries
    ]


def _generic_subject(user_text: str) -> str:
    """Sujet d'une demande hors téléphones : "un dossier sur l'énergie solaire"."""
    match = re.search(
        r"\b(?:sur|concernant|à propos de|a propos de)\s+(.+)$",
        str(user_text or ""),
        flags=re.IGNORECASE,
    )
    return _clean(match.group(1)) if match else ""


def _build_generic_steps(subject: str) -> List[PlannerStep]:
    year = datetime.now().year
    queries = [
        ("search_overview", subject, "obtenir une vue d'ensemble fiable du sujet"),
        ("search_facts", f"{subject} chiffres clés données", "recueillir des faits et chiffres vérifiables"),
        ("search_news", f"{subject} actualité {year}", "trouver les informations récentes"),
    ]
    return [
        PlannerStep(
            step_id=step_id,
            action="search",
            tool_name="web_search",
            args={"query": _clean(query), "num_results": 5},
            purpose=purpose,
        )
        for step_id, query, purpose in queries
    ]


def build_deep_research_plan(user_text: str, context: Any = None) -> Optional[PlannerPlan]:
    if not is_deep_research_request(user_text):
        return None
    subject = _extract_subject(user_text, context)
    if subject:
        steps = _build_steps(subject, user_text)
    else:
        # Sujet hors téléphones : recherches génériques (avant, la demande
        # recevait "Sur quel sujet… ?" alors que le sujet était donné).
        subject = _generic_subject(user_text)
        if not subject:
            return None
        steps = _build_generic_steps(subject)
    return PlannerPlan(
        kind="deep_research",
        objective=f"collecter les informations importantes et vérifiables sur {subject}",
        tools=["web_search"],
        constraints={},
        models=[subject],
        steps=steps,
        requires_synthesis=True,
        version="0.6",
    )


__all__ = ["is_deep_research_request", "build_deep_research_plan"]
