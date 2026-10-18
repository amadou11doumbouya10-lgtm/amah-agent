"""Briques communes du traitement d'un message, pour les 3 interfaces
(gui.py, voice_fullscreen.py, agent.py) — première pièce du futur Amah Core.

Avant, chaque interface avait sa version (ou n'en avait pas) : l'interface
vocale envoyait les résultats d'outils au modèle sans les tronquer, coupait
son historique sans protéger les paires appel d'outil / résultat et ne
journalisait pas ses erreurs (banc des 3 interfaces, 18/10/2026).
"""
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path

ERROR_LOG = (Path(sys.executable).parent if getattr(sys, "frozen", False)
             else Path(__file__).resolve().parent.parent) / "amah_errors.log"


def log_error(context: str, exc: BaseException) -> None:
    """Ajoute l'erreur (avec la pile d'appels) à amah_errors.log, limité à ~500 Ko."""
    try:
        if ERROR_LOG.exists() and ERROR_LOG.stat().st_size > 500_000:
            ERROR_LOG.write_text(ERROR_LOG.read_text(encoding="utf-8", errors="replace")[-250_000:],
                                 encoding="utf-8")
        trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        with ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] {context}\n{trace}")
    except Exception:
        pass


# Pages web : 4 000 caractères pour pouvoir résumer un article (les 2 000
# premiers ne contiennent souvent que le chapeau) ; le reste : 2 000.
LONG_RESULT_TOOLS = {"get_page_text", "read_webpage"}


def clip_tool_result(tool_name, result: str) -> str:
    """Tronque un résultat d'outil avant de l'envoyer au modèle (tokens)."""
    from tools import resolve_tool_name
    result = str(result)
    limit = 4000 if resolve_tool_name(tool_name) in LONG_RESULT_TOOLS else 2000
    if len(result) > limit:
        return result[:limit] + "\n...[tronqué pour économiser les tokens]"
    return result


def trim_history(messages: list, max_messages: int) -> list:
    """[system] + les max_messages derniers messages, sans résultat d'outil
    orphelin en tête : Groq refuse un message "tool" qui ne suit pas l'appel
    correspondant. Une coupure naïve tombait dessus dès qu'un tour contenait
    plusieurs appels d'outils parallèles (84 % des conversations simulées de
    15 échanges avec l'interface vocale)."""
    if len(messages) <= max_messages + 1:
        return messages
    tail = messages[-max_messages:]
    while tail and tail[0].get("role") == "tool":
        tail = tail[1:]
    return [messages[0]] + tail


_INLINE_MD = [
    (re.compile(r"!\[([^\]]*)\]\([^)]*\)"), r"\1"),          # images
    (re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"),            # liens : le texte seul
    (re.compile(r"(\*\*|__)(.+?)\1"), r"\2"),                 # gras
    (re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"), r"\1"),  # italique *x*
    (re.compile(r"`([^`]+)`"), r"\1"),                        # code en ligne
]
_TABLE_RULE = re.compile(r"\|?[\s:|-]{3,}\|?")


def speech_text(text: str) -> str:
    """Texte à prononcer : sans Markdown (sinon la synthèse vocale lit les
    astérisques et les dièses des réponses du modèle, ex. "**3.14.8**").
    Une ligne (titre, puce, ligne de tableau) devient une phrase."""
    out = re.sub(r"```.*?```", " ", str(text or ""), flags=re.DOTALL)
    sentences = []
    for line in out.splitlines():
        line = line.strip()
        if not line or _TABLE_RULE.fullmatch(line):
            continue
        line = re.sub(r"^(?:#{1,6}|>|[-*•])\s*", "", line)     # titre, citation, puce
        if line.count("|") >= 2:                                # ligne de tableau
            line = ", ".join(c.strip() for c in line.strip("|").split("|") if c.strip())
        for pattern, repl in _INLINE_MD:
            line = pattern.sub(repl, line)
        line = re.sub(r"\s{2,}", " ", line).strip()
        if line:
            sentences.append(line if re.search(r"[.!?:;,…]$", line) else line + ".")
    return " ".join(sentences)
