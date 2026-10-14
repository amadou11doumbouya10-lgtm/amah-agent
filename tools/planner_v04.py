"""
Amah Agent — Planner / Reasoner V0.4

Orchestrateur local pour les demandes complexes.

Principes :
- Le planner ne fait aucun appel LLM.
- Une comparaison explicite produit un vrai plan multi-étapes.
- Chaque modèle/option dispose de sa propre recherche indépendante.
- Les étapes sont ordonnées, mais les recherches indépendantes peuvent être
  exécutées directement par l'agent sans repasser par le LLM.
- Le plan fournit les contraintes actives et les critères de synthèse.

Compatible Python 3.9.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _norm(text: str) -> str:
    text = str(text or "").lower().strip()
    table = str.maketrans({
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "î": "i", "ï": "i", "ô": "o", "ö": "o",
        "ù": "u", "û": "u", "ü": "u", "ç": "c",
    })
    return re.sub(r"\s+", " ", text.translate(table))


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t.,;:!?\"'")


def _explicit_models(text: str) -> List[str]:
    found: List[str] = []
    pattern = (
        r"\b(?:iphone|ipad|macbook|pixel|galaxy)\s*"
        r"(?:\d{1,2}(?:\s+(?:pro|max|air|plus))?|[A-Za-z0-9-]+)\b"
    )
    for match in re.findall(pattern, str(text or ""), flags=re.IGNORECASE):
        value = _clean(match)
        if value and value.lower() not in [m.lower() for m in found]:
            found.append(value)
    return found[-5:]


def _context_models(context: Any) -> List[str]:
    values = getattr(context, "explicit_subjects", []) if context is not None else []
    result: List[str] = []
    for value in values or []:
        value = _clean(str(value))
        if value and value.lower() not in [m.lower() for m in result]:
            result.append(value)
    return result[-5:]


def _constraints(context: Any) -> Dict[str, str]:
    return dict(getattr(context, "constraints", {}) or {}) if context is not None else {}


def _topic(context: Any, models: List[str], text: str) -> str:
    value = str(getattr(context, "topic", "") or "").strip() if context is not None else ""
    if value:
        return value
    if models:
        return models[0]
    return _clean(text)[:80]


def _is_complex(text: str) -> bool:
    n = _norm(text)
    if len(n.split()) < 5:
        return False
    triggers = (
        "compare", "comparer", "comparatif", "comparaison", "difference",
        "recommande", "recommandation", "meilleur", "meilleure",
        "choisir", "lequel", "laquelle", "adapte", "adapté",
        "pour moi", "plusieurs", "top ", "classe", "analyse",
        "strategie", "strategique", "budget", "selon", "en fonction",
        "entre ",
    )
    return any(trigger in n for trigger in triggers)


def _comparison_requested(text: str) -> bool:
    n = _norm(text)
    return bool(re.search(r"\b(?:compare|comparer|comparatif|comparaison|difference|entre)\b", n))


def _recommendation_requested(text: str) -> bool:
    n = _norm(text)
    return bool(re.search(r"\b(?:recommande|recommandation|meilleur|meilleure|choisir|lequel|laquelle)\b", n))


def _research_requested(text: str) -> bool:
    n = _norm(text)
    return bool(re.search(r"\b(?:cherche|recherche|trouve|prix|acheter|offre|disponible)\b", n))


def _criteria(constraints: Dict[str, str]) -> List[str]:
    result = ["prix", "disponibilité"]
    if "sans" in constraints:
        result.append(constraints["sans"])
    if "priorite" in constraints:
        result.append(constraints["priorite"])
    if "budget" in constraints:
        result.append("respect du budget")
    return result


def _market_hint(constraints: Dict[str, str], topic: str) -> str:
    """Ajoute le marché uniquement lorsqu'il est suggéré par le contexte."""
    context = " ".join(str(v) for v in constraints.values()) + " " + str(topic or "")
    n = _norm(context)
    if "gnf" in n or "guinee" in n or "guinea" in n or "conakry" in n:
        return "Guinée Conakry"
    return ""


def _connectivity_hint(constraints: Dict[str, str]) -> str:
    value = _norm(constraints.get("sans", ""))
    if "esim" in value:
        return "version avec SIM physique"
    return ""


def _budget_hint(constraints: Dict[str, str]) -> str:
    value = _clean(constraints.get("budget", ""))
    if not value:
        return ""
    normalized = _norm(value)
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(millions?|m)\b", normalized)
    if m and "gnf" in normalized:
        return f"moins de {m.group(1).replace(',', '.')} millions GNF"
    m = re.search(r"(\d[\d\s.,]*)\s*gnf\b", normalized)
    if m:
        number = re.sub(r"[^0-9]", "", m.group(1))
        if number:
            return f"moins de {number} GNF"
    return f"budget {value}"


def _search_query(model: str, constraints: Dict[str, str], topic: str) -> str:
    """Construit une requête orientée marché + prix + contraintes."""
    parts = [model]
    market = _market_hint(constraints, topic)
    if market:
        parts.append(market)
    budget = _budget_hint(constraints)
    if budget:
        parts.append(budget)
    connectivity = _connectivity_hint(constraints)
    if connectivity:
        parts.append(connectivity)
    if "priorite" in constraints:
        parts.append(f"priorité {constraints['priorite']}")
    parts.extend(["prix", "caractéristiques"])
    return _clean(" ".join(parts))


@dataclass
class PlannerStep:
    step_id: str
    action: str
    tool_name: str
    args: Dict[str, Any] = field(default_factory=dict)
    purpose: str = ""
    depends_on: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "tool_name": self.tool_name,
            "args": dict(self.args),
            "purpose": self.purpose,
            "depends_on": list(self.depends_on),
        }


@dataclass
class PlannerPlan:
    kind: str
    objective: str
    tools: List[str] = field(default_factory=list)
    constraints: Dict[str, str] = field(default_factory=dict)
    models: List[str] = field(default_factory=list)
    steps: List[PlannerStep] = field(default_factory=list)
    clarification: str = ""
    requires_synthesis: bool = True
    version: str = "0.4"

    @property
    def executable(self) -> bool:
        return bool(self.steps)

    def prompt_hint(self) -> str:
        lines = [
            "[PLAN LOCAL V0.4]",
            f"type={self.kind}",
            f"objectif={self.objective}",
        ]
        if self.models:
            lines.append("modeles=" + ", ".join(self.models))
        for key, value in self.constraints.items():
            lines.append(f"{key}={value}")
        lines.append("outils=" + ", ".join(self.tools))
        if self.steps:
            lines.append("etapes:")
            for step in self.steps:
                args = ", ".join(f"{k}={v!r}" for k, v in step.args.items())
                lines.append(
                    f"  {step.step_id}: {step.action} -> {step.tool_name}({args})"
                )
        if self.kind == "comparison":
            lines.append(
                "Compare uniquement les modèles réellement recherchés et respecte les contraintes explicites."
            )
        lines.append("Ne fabrique aucun fait absent des résultats des outils.")
        lines.append("Pour la connectivité, Cash ou paiement Cash ne prouve jamais la présence d’une SIM physique.")
        lines.append("Ne transforme pas sans eSIM en SIM physique sauf si une source le confirme explicitement.")
        lines.append("Pour une comparaison, chaque modèle doit avoir ses propres résultats ; si une donnée est absente, indique non vérifié.")
        return "\n".join(lines)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "kind": self.kind,
            "objective": self.objective,
            "tools": list(self.tools),
            "constraints": dict(self.constraints),
            "models": list(self.models),
            "steps": [step.as_dict() for step in self.steps],
            "clarification": self.clarification,
            "requires_synthesis": self.requires_synthesis,
        }


def build_plan(user_text: str, context: Any = None) -> Optional[PlannerPlan]:
    if not _is_complex(user_text):
        return None

    text = str(user_text or "").strip()
    constraints = _constraints(context)
    models = _explicit_models(text)
    contextual_models = _context_models(context)
    if not models:
        models = contextual_models

    topic = _topic(context, models, text)

    if _comparison_requested(text):
        if len(models) < 2:
            # "compare Python et JavaScript", "liste les fichiers entre…" : pas
            # une comparaison de modèles identifiés -> le LLM s'en charge.
            return None

        steps: List[PlannerStep] = []
        for index, model in enumerate(models[:4], start=1):
            steps.append(
                PlannerStep(
                    step_id=f"search_{index}",
                    action="search",
                    tool_name="web_search",
                    args={
                        "query": _search_query(model, constraints, topic),
                        "num_results": 5,
                    },
                    purpose=f"recueillir les informations disponibles sur {model}",
                )
            )

        return PlannerPlan(
            kind="comparison",
            objective="comparer les options demandées selon les contraintes actives",
            tools=["web_search"],
            constraints=constraints,
            models=models[:4],
            steps=steps,
            requires_synthesis=True,
        )

    # Un plan de recherche n'a de sens que pour des produits identifiés ou un
    # vrai contexte d'achat ; sinon "quel est le meilleur moyen de zipper un
    # dossier" ou "trouve le fichier X" partaient en recherche web.
    shopping = bool(re.search(
        r"\b(?:prix|acheter|achat|offre|disponible|budget|gnf|fcfa)\b", _norm(text)
    ))
    if (_recommendation_requested(text) or _research_requested(text)) and (models or shopping):
        query_parts = [topic]
        if models:
            query_parts = models[:4]
        if "budget" in constraints:
            query_parts.append(f"budget {constraints['budget']}")
        if "sans" in constraints:
            query_parts.append(f"sans {constraints['sans']}")
        if "priorite" in constraints:
            query_parts.append(f"priorité {constraints['priorite']}")
        query = _clean(" ".join(str(x) for x in query_parts if x))
        return PlannerPlan(
            kind="research_recommendation",
            objective="trouver des options pertinentes puis produire une recommandation",
            tools=["web_search"],
            constraints=constraints,
            models=models[:4],
            steps=[
                PlannerStep(
                    step_id="search_1",
                    action="search",
                    tool_name="web_search",
                    args={"query": query, "num_results": 5},
                    purpose="recueillir les options pertinentes",
                )
            ],
            requires_synthesis=True,
        )

    # Plus de plan "analysis" générique : il transformait toute phrase contenant
    # "analyse", "selon", "pour moi"… en recherche web sur la phrase elle-même
    # ("analyse le fichier ventes.xlsx" -> web_search "analyse fichier C Users").
    return None


__all__ = ["PlannerStep", "PlannerPlan", "build_plan"]
