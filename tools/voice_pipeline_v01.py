"""Amah Agent — Voice Pipeline V0.1.

Relie l'outil listen() au pipeline conversationnel normal :
écoute -> texte reconnu -> traitement Amah -> réponse vocale.
Compatible Python 3.9.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Tuple

_TRIGGER_PATTERNS = (
    r"^ecoute ma voix$",
    r"^ecoute moi$",
    r"^ecoute moi parler$",
    r"^ecoute ma commande$",
    r"^mode vocal$",
    r"^commande vocale$",
    r"^parle avec moi$",
)


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", str(text or ""))
        if unicodedata.category(ch) != "Mn"
    )


def normalize(text: str) -> str:
    text = _strip_accents(text).lower().strip()
    text = re.sub(r"[!?.,;:]+$", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def is_voice_listen_request(text: str) -> bool:
    normalized = normalize(text)
    return any(re.match(pattern, normalized, flags=re.IGNORECASE) for pattern in _TRIGGER_PATTERNS)



def normalize_spoken_command(text: str) -> str:
    """Nettoie quelques erreurs courantes de reconnaissance vocale sans ajouter d'intention."""
    value = str(text or "").strip()
    if not value:
        return value

    # URL dictée : "https 2 slash 2 slash exemple point com".
    value = re.sub(r"\bhttps?\s+(?:2|deux)\s+slash\s+(?:2|deux)\s+slash\s*",
                   lambda m: "https://" if m.group(0).lower().startswith("https") else "http://",
                   value, flags=re.IGNORECASE)
    value = re.sub(r"\bhttp\s+(?:2|deux)\s+slash\s+(?:2|deux)\s+slash\s*",
                   "http://", value, flags=re.IGNORECASE)
    value = re.sub(r"\bpoint\s+(com|fr|net|org|gn|io|dev)\b", r".\1", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+\.(com|fr|net|org|gn|io|dev)\b", r".\1", value, flags=re.IGNORECASE)

    if re.search(r"https?://", value, flags=re.IGNORECASE):
        value = re.sub(r"\s+slash\s+", "/", value, flags=re.IGNORECASE)
        value = re.sub(r"(?i)(https?://)\s+", r"\1", value)

    return re.sub(r"\s+", " ", value).strip(" \t\r\n,.;:!?-")


def voice_local_clarification(text: str) -> str:
    """Clarifie localement des commandes vocales incomplètes."""
    normalized = normalize(text)
    if re.fullmatch(r"ouvre(?: le| un| la)? html", normalized):
        return "Quel fichier HTML ou quelle URL souhaites-tu que j'ouvre ?"
    if re.fullmatch(r"ouvre(?: vision ama| vision a ma)", normalized):
        return "Quel élément de Vision-Amah souhaites-tu ouvrir ? Donne-moi son URL ou son chemin."
    if normalized == "ouvre":
        return "Que souhaites-tu que j'ouvre ? Donne-moi une URL, un fichier ou un dossier."
    return ""

def parse_listen_result(raw_result: object) -> Tuple[bool, str, str]:
    """Retourne (ok, texte_reconnu, erreur) depuis le résultat sérialisé de l'outil."""
    if isinstance(raw_result, dict):
        data = raw_result
    else:
        try:
            data = json.loads(str(raw_result or ""))
        except Exception:
            return False, "", "Résultat de reconnaissance vocale illisible."

    if not isinstance(data, dict):
        return False, "", "Résultat de reconnaissance vocale invalide."

    if data.get("error"):
        return False, "", str(data.get("error"))

    text = str(data.get("texte") or data.get("text") or "").strip()
    if not text:
        return False, "", "Aucun texte n'a été reconnu."

    return True, text, ""


def clean_for_speech(reply: object, max_chars: int = 650) -> str:
    """Réduit une réponse Amah à une phrase adaptée à la synthèse vocale."""
    text = str(reply or "").strip()
    if not text:
        return ""

    # Les gros JSON/résultats techniques ne sont pas agréables à lire à voix haute.
    if text.startswith("{") or text.startswith("[") or "\"resultats\"" in text:
        return "J'ai terminé. Le résultat détaillé est affiché à l'écran."

    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_#`]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:") + ". Le reste est affiché à l'écran."
    return text
