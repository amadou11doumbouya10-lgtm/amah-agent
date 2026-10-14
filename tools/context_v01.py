"""
Amah Agent — Context Manager V0.7

Contexte actif compact et prudent.
- Conserve uniquement les informations stables explicites.
- N'injecte plus les anciennes query/location/url d'actions dans le contexte actif.
- Détecte quelques références de suivi pour éviter les recherches arbitraires.
- Aucun appel LLM et aucune modification SQLite.

Compatible Python 3.9.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional


_STOPWORDS = {
    "a", "au", "aux", "avec", "ce", "ces", "cette", "dans", "de", "des",
    "du", "en", "et", "est", "faire", "fais", "il", "je", "la", "le", "les",
    "me", "mon", "ma", "mes", "moi", "ne", "nous", "on", "ou", "par", "pour",
    "que", "quel", "quelle", "quelles", "quels", "sur", "ta", "te", "tes", "toi",
    "tu", "un", "une", "vers", "vous", "à", "ça", "cela", "veux", "voudrais",
    "aimerais", "cherche", "recherche", "donne", "comparer", "maintenant", "alors",
}


def _norm(text: str) -> str:
    text = str(text or "").lower().strip()
    replacements = str.maketrans({
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "î": "i", "ï": "i", "ô": "o", "ö": "o",
        "ù": "u", "û": "u", "ü": "u", "ç": "c",
    })
    return re.sub(r"\s+", " ", text.translate(replacements))


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t.,;:!?\"'")


def _first(patterns: Iterable[str], text: str) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = _clean(match.group(1))
            if value:
                return value
    return None


def _topic_from_objective(objective: str) -> Optional[str]:
    value = _clean(objective)
    patterns = (
        r"^(?:de )?(?:comparer|acheter|choisir|trouver|chercher|lancer|creer|créer|preparer|préparer)\s+(?:un|une|des|le|la|les)?\s*(.+)$",
        r"^(?:de )?(?:faire|faire une|faire un)\s+(.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            candidate = _clean(match.group(1))
            if candidate:
                return candidate
    return None


class ConversationContext:
    __slots__ = (
        "turns", "topic", "objective", "entities", "constraints",
        "last_user", "explicit_subjects",
    )

    def __init__(self) -> None:
        self.turns = 0
        self.topic = ""
        self.objective = ""
        self.entities: Dict[str, str] = {}
        self.constraints: Dict[str, str] = {}
        self.last_user = ""
        self.explicit_subjects = []

    @classmethod
    def from_messages(cls, messages: Iterable[Dict[str, Any]]) -> "ConversationContext":
        """Reconstruit uniquement les éléments stables depuis l'historique.

        Une ancienne commande d'action (écran, navigateur, recherche, etc.) ne
        devient pas automatiquement le sujet de la nouvelle session.
        """
        context = cls()
        for message in messages:
            if str(message.get("role", "")) != "user":
                continue
            text = str(message.get("content", "") or "")
            if not text.strip():
                continue
            normalized = _norm(text)
            explicit_objective = bool(
                re.match(
                    r"^(?:je veux|je voudrais|j aimerais|j ai besoin de|mon objectif est)\b",
                    normalized,
                )
            )
            explicit_model = bool(
                re.search(
                    r"\b(?:iphone|ipad|macbook|pixel|galaxy)\s*(?:\d{1,2}(?:\s+(?:pro|max|air|plus))?|[A-Za-z0-9-]+)\b",
                    text, flags=re.IGNORECASE,
                )
            )
            stable_constraint = bool(
                re.search(
                    r"\b(?:mon|notre)\s+budget\b|\b(?:sans|avec)\s+(?:e?sim|wifi|bluetooth)\b|\b(?:priorite|priorité)\b",
                    normalized,
                )
            )
            if explicit_objective or explicit_model or stable_constraint:
                context.ingest(
                    text,
                    emit=False,
                    capture_transient=False,
                    infer_topic=(explicit_objective or explicit_model),
                )
        return context

    def ingest(
        self,
        text: str,
        emit: bool = False,
        capture_transient: bool = True,
        infer_topic: bool = True,
    ) -> None:
        text = str(text or "").strip()
        if not text:
            return

        self.turns += 1
        self.last_user = text
        normalized = _norm(text)

        objective = _first(
            (
                r"\b(?:je veux|j aimerais|j ai besoin de|mon objectif est|on doit|nous devons)\s+(.+)$",
                r"\b(?:je cherche a|je cherche à|je voudrais)\s+(.+)$",
            ),
            text,
        )
        if objective:
            self.objective = objective

        subject = _first(
            (r"\b(?:sur|pour|concernant|a propos de|à propos de)\s+(.+)$",),
            text,
        )
        objective_topic = _topic_from_objective(objective) if objective else None
        if infer_topic:
            if subject:
                self.topic = subject
            elif objective_topic:
                self.topic = objective_topic
            elif not self.topic:
                # Ne jamais transformer une commande d'action en sujet actif.
                # Exemples : « ouvre https://… », « lis ce fichier »,
                # « regarde mon écran », « exécute ipconfig ».
                action_lead = bool(
                    re.match(
                        r"^(?:ouvre|ouvrir|lance|lancer|lis|lire|regarde|regarder|exécute|execute)\b",
                        normalized,
                    )
                )
                if not action_lead:
                    words = [
                        w for w in re.findall(r"[A-Za-zÀ-ÿ0-9_-]+", text)
                        if _norm(w) not in _STOPWORDS
                    ]
                    if words:
                        self.topic = " ".join(words[:5])

        # Retenir les modèles explicitement nommés par l'utilisateur.
        models = re.findall(r"\b(?:iphone|ipad|macbook|pixel|galaxy)\s*(?:\d{1,2}(?:\s+(?:pro|max|air|plus))?|[A-Za-z0-9-]+)\b", text, flags=re.IGNORECASE)
        for model in models:
            cleaned = _clean(model)
            if cleaned and cleaned.lower() not in [m.lower() for m in self.explicit_subjects]:
                self.explicit_subjects.append(cleaned)
        self.explicit_subjects = self.explicit_subjects[-5:]
        if infer_topic and models:
            self.topic = ", ".join(self.explicit_subjects[-3:])

        # Les valeurs transitoires ne sont JAMAIS reconstruites depuis l'historique.
        if capture_transient:
            url = re.search(r"https?://\S+", text, flags=re.IGNORECASE)
            if url:
                self.entities["url"] = url.group(0).rstrip(".,;:!?)]}>")

            search = _first(
                (r"\b(?:cherche|recherche)(?:\s+sur)?\s+(?:google|internet|le web)\s+(.+)$",),
                normalized,
            )
            if search:
                self.entities["query"] = search

            location = _first(
                (
                    r"\b(?:meteo|météo|temps)\s+(?:a|à|de|du|dans)\s+(.+)$",
                    r"\b(?:de|a|à|dans)\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ -]{1,50})$",
                ),
                text,
            )
            if location and len(location) < 60:
                self.entities["location"] = location

        budget = re.search(
            r"\b(?:(?:mon|notre)\s+budget(?:\s+(?:est|sera))?|budget|pour|avec)\s*(?:de|d environ|d'environ)?\s*([0-9][0-9\s.,]*)(?:\s*(millions?|m|k))?\s*(gnf|fcfa|eur|€|dollars?|usd)\b",
            normalized,
            flags=re.IGNORECASE,
        )
        if budget:
            amount = _clean(budget.group(1))
            multiplier = _clean(budget.group(2) or "")
            currency = _clean(budget.group(3))
            self.constraints["budget"] = " ".join(
                part for part in (amount, multiplier, currency) if part
            )

        for key, patterns in {
            "sans": (r"\b(?:sans|je ne veux pas|je veux eviter|je veux éviter)\s+(.+)$",),
            "priorite": (r"\b(?:priorite|priorité|je privilegie|je privilégie)\s*[:]?\s*(.+)$",),
        }.items():
            value = _first(patterns, text)
            if value:
                self.constraints[key] = value

        if re.match(r"^(et|et pour|et si|et avec|alors|du coup)\b", normalized):
            if self.topic and self.topic not in normalized:
                self.entities["followup_of"] = self.topic

    def is_context_statement(self, text: str) -> bool:
        """Détecte une déclaration d'objectif sans demande d'exécution immédiate."""
        normalized = _norm(text)
        if re.match(r"^(?:je veux|je voudrais|j aimerais|j ai besoin de|mon objectif est)\b", normalized):
            return True
        return False

    def has_explicit_model(self) -> bool:
        return bool(self.explicit_subjects)

    def latest_explicit_model(self) -> str:
        return self.explicit_subjects[-1] if self.explicit_subjects else ""

    def looks_like_ambiguous_model_followup(self, text: str) -> bool:
        normalized = _norm(text)
        return bool(
            re.search(r"\b(?:modele|modèle)\s+(?:precedent|précédent|d avant)\b", normalized)
            or re.search(r"\b(?:celui|celle)\s+(?:d avant|precedent|précédent)\b", normalized)
            or re.search(r"\bcompare(?:r)?\s+(?:maintenant|ça|cela)\b", normalized)
        ) and not self.has_explicit_model()

    def is_pure_context_update(self, text: str) -> bool:
        normalized = _norm(text)
        return bool(
            re.match(r"^(?:mon|notre)\s+budget\b", normalized)
            or re.match(r"^et\s+(?:sans|avec|pour)\b", normalized)
            or re.match(r"^(?:sans|avec)\s+e?sim\b", normalized)
            or re.match(r"^(?:priorite|priorite:)\b", normalized)
        )

    def summary_line(self) -> str:
        parts = []
        if self.topic:
            parts.append(f"sujet={self.topic[:60]}")
        if self.objective:
            parts.append(f"objectif={self.objective[:70]}")
        if self.explicit_subjects:
            parts.append(f"modeles={', '.join(self.explicit_subjects[-3:])}")
        # Les query/location/url ne sont pas des éléments stables : ne pas les injecter.
        for key in ("budget", "priorite", "sans"):
            if key in self.constraints:
                parts.append(f"{key}={self.constraints[key][:70]}")
        return " | ".join(parts)

    def format_hint(self) -> str:
        summary = self.summary_line()
        if not summary:
            return ""
        return (
            "[CONTEXTE ACTIF — faits explicites seulement]\n"
            + summary
            + "\nN'utilise ce contexte que pour résoudre une référence de suivi. "
              "Les instructions du message courant sont toujours prioritaires. "
              "N'invente aucun modèle, prix, URL ou recherche absent du message courant."
        )

    def snapshot(self) -> Dict[str, Any]:
        return {
            "turns": self.turns,
            "topic": self.topic,
            "objective": self.objective,
            "entities": dict(self.entities),
            "constraints": dict(self.constraints),
            "last_user": self.last_user,
            "explicit_subjects": list(self.explicit_subjects),
        }


__all__ = ["ConversationContext"]
