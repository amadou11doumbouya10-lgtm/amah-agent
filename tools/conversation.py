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
from types import SimpleNamespace
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


def drop_old_tool_results(messages: list, keep_requests: int = 2) -> list:
    """Retire les appels d'outils et leurs résultats des demandes anciennes :
    seules les keep_requests dernières demandes (celle en cours comprise) les
    gardent ; les réponses d'Amah restent. Avant, chaque page lue ou recherche
    repartait à chaque appel : ~7 000 tokens par appel dans l'interface vocale
    et clés Groq épuisées 3 fois en 20 minutes (journal du 19/10/2026)."""
    users = [i for i, m in enumerate(messages) if m.get("role") == "user"]
    if len(users) <= keep_requests:
        return messages
    cut = users[-keep_requests]
    out = []
    for i, m in enumerate(messages):
        if i < cut and m.get("role") == "tool":
            continue
        if i < cut and m.get("tool_calls"):
            if not str(m.get("content") or "").strip():
                continue
            m = {k: v for k, v in m.items() if k != "tool_calls"}
        out.append(m)
    return out


# Outils du navigateur : si la demande précédente en a utilisé un, la suite
# ("et le champ e-mail", "clique sur…") reçoit les quatre
_BROWSER_TOOLS = ("open_browser", "get_page_text", "click_text", "type_in_field")


def recent_tool_names(messages: list) -> list:
    """Noms des outils appelés pendant la demande précédente (entre les deux
    derniers messages de l'utilisateur)."""
    users = [i for i, m in enumerate(messages) if m.get("role") == "user"]
    if not users:
        return []
    start = users[-2] if len(users) >= 2 else 0
    names = []
    for m in messages[start:users[-1]]:
        for tc in m.get("tool_calls") or []:
            name = (tc.get("function") or {}).get("name")
            if name and name not in names:
                names.append(name)
    return names


def with_recent_tools(tools, messages: list, definitions: list):
    """Ajoute aux outils proposés ceux de la demande précédente : une suite ne
    reprend pas toujours les mots qui les déclenchent ("il y a un champ
    contact, mets mon numéro" -> outils de fichiers proposés, type_in_field
    manquant, erreur 400 de Groq ; journal du 19/10/2026). Conversation pure
    (aucun outil) : inchangé."""
    if not tools:
        return tools
    from tools import resolve_tool_name
    names = {resolve_tool_name(n) for n in recent_tool_names(messages)}
    if names & set(_BROWSER_TOOLS):
        names |= set(_BROWSER_TOOLS)
    have = {t["function"]["name"] for t in tools}
    return list(tools) + [d for d in definitions
                          if d["function"]["name"] in names and d["function"]["name"] not in have]


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


# Tours d'outils par demande. Sans limite, le modèle peut tourner en rond :
# test réel du 19/10/2026, "liste mes projets sur YouTube" -> 12 tours de
# recherches web (~72 000 tokens), clés Groq épuisées, aucune réponse.
MAX_TOOL_ROUNDS = 5
WRAP_UP_REQUEST = ("N'appelle plus aucun outil : réponds maintenant à ma demande avec ce que "
                   "tu as trouvé, et dis simplement ce que tu n'as pas trouvé.")
WRAP_UP_FALLBACK = ("Je n'ai pas trouvé de réponse fiable après plusieurs recherches. "
                    "Peux-tu préciser ta demande ?")


def _flat_history(messages: list) -> list:
    """L'historique sans appels ni résultats d'outils : ceux de la demande en
    cours deviennent du texte dans un dernier message. Avec des messages "tool"
    sous les yeux, gpt-oss appelle encore un outil même quand aucun n'est
    disponible (erreur 400 tool_use_failed, test réel du 19/10/2026)."""
    last_user = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=0)
    plain = [m for m in messages[:last_user + 1]
             if m.get("role") in ("system", "user")
             or (m.get("role") == "assistant" and not m.get("tool_calls"))]
    found = []
    for m in messages[last_user + 1:]:
        for tc in m.get("tool_calls") or []:
            fn = tc.get("function", {})
            found.append(f"- outil {fn.get('name')} {fn.get('arguments') or ''}".rstrip())
        if m.get("role") == "tool":
            found.append(f"  résultat : {str(m.get('content', ''))[:600]}")
    request = WRAP_UP_REQUEST
    if found:
        request = "Outils déjà utilisés pour ma demande :\n" + "\n".join(found) + "\n\n" + request
    return plain + [{"role": "user", "content": request}]


def wrap_up(call, messages):
    """Dernière réponse, sans outil, après MAX_TOOL_ROUNDS tours d'outils.
    call(messages) appelle le modèle SANS outils. Renvoie une réponse au format
    du client (choices[0].message.content) ; si l'appel échoue, un message
    d'excuse plutôt qu'une erreur."""
    text = ""
    try:
        text = (call(_flat_history(messages)).choices[0].message.content or "").strip()
    except Exception as e:
        log_error("réponse finale sans outil", e)
    message = SimpleNamespace(content=text or WRAP_UP_FALLBACK, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=message)])


_INLINE_MD = [
    (re.compile(r"!\[([^\]]*)\]\([^)]*\)"), r"\1"),          # images
    (re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"),            # liens : le texte seul
    (re.compile(r"(\*\*|__)(.+?)\1"), r"\2"),                 # gras
    (re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"), r"\1"),  # italique *x*
    (re.compile(r"`([^`]+)`"), r"\1"),                        # code en ligne
]
_TABLE_RULE = re.compile(r"\|?[\s:|-]{3,}\|?")


_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
         "septembre", "octobre", "novembre", "décembre"]


def today_line() -> str:
    """Date et heure du jour, pour le prompt. Sans elle, le modèle supposait la
    date de son entraînement : il cherchait "l'actualité d'octobre 2024" en
    2026 (test réel du 18/10/2026)."""
    now = datetime.now()
    return (f"Aujourd'hui : {_JOURS[now.weekday()]} {now.day} {_MOIS[now.month - 1]} "
            f"{now.year}, il est {now.hour} h {now:%M} (heure du PC).")


# Mots que la reconnaissance vocale déforme chez l'utilisateur (vus dans le
# journal de session, 18-19/10/2026). Appliqué au texte entendu avant de le
# comprendre ; une erreur de transcription ici coûtait un échange entier.
TRANSCRIPT_FIXES = [
    # "GitHub" prononcé à la française
    (re.compile(r"\b(?:jet|git|guit|gîte|gite|guide|dip|diff)[\s-]?(?:top|tope|hub|heub|tub|up)\b", re.I), "GitHub"),
    (re.compile(r"\bdiptop\b|\blient? dit op\b", re.I), "GitHub"),
    # "champ de texte" (le champ de saisie de l'interface vocale)
    (re.compile(r"\b(?:cha[iî]ne|chain|chant|chat|champs?)\s+de\s+(?:test|teste|texte|tests)\b", re.I), "champ de texte"),
    # Champs d'un formulaire dictés : "chambre de contact", "un chat mail"
    (re.compile(r"\bchambre\s+de\s+(contact|saisie|texte|recherche|t[ée]l[ée]phone|nom)\b", re.I), r"champ de \1"),
    (re.compile(r"\b(?:chat|chant)\s+(e-?mail|mail)\b", re.I), r"champ \1"),
    # "mon compte GitHub" entendu "mon compte du top"
    (re.compile(r"\bcompte\s+(?:du|de)\s+top\b", re.I), "compte GitHub"),
    # "Amah" en tête de phrase : "à moi", "ama", "Hama", "ahma", "Amma" (pas "Emma" : vrai prénom)
    (re.compile(r"^(?:à|a)\s+moi\b[\s,]*|^(?:ama|amma|hama|ahma)\b[\s,]*", re.I), "Amah, "),
]


# "GitHub" entendu "YouTube" par Google (confirmé par l'utilisateur, 19/10/2026) :
# corrigé seulement quand la phrase parle de projets ou de code, jamais de
# vidéos ni de musique ("ouvre YouTube" reste YouTube)
_YOUTUBE_FOR_GITHUB = re.compile(
    r"\b(?P<ctx>(?:projets?|d[ée]p[ôo]ts?|repos?|codes?|commits?)\b[^.?!]{0,25}?)you\s?tube\b"
    r"|\byou\s?tube(?=\s+(?:projets?|d[ée]p[ôo]ts?|repos?)\b)", re.I)
_VIDEO_WORDS = re.compile(r"vid[ée]o|cha[iî]ne|musique|chanson|clip|abonn", re.I)


def fix_transcript(text: str) -> str:
    """Texte entendu par la reconnaissance vocale -> texte corrigé."""
    out = str(text or "").strip()
    for pattern, repl in TRANSCRIPT_FIXES:
        out = pattern.sub(repl, out)
    if not _VIDEO_WORDS.search(out):
        out = _YOUTUBE_FOR_GITHUB.sub(lambda m: (m.group("ctx") or "") + "GitHub", out)
    return re.sub(r"\s{2,}", " ", out).strip(" ,") or str(text or "")


def spoken_excerpt(text: str, limit: int = 450):
    """(texte à dire ET à afficher, coupé ?) : la réponse sans Markdown, coupée
    à la fin d'une phrase avant `limit` caractères. Avant, l'écran montrait 220
    caractères bruts et la voix en lisait 450, coupés au milieu d'une phrase :
    on n'entendait pas ce qu'on lisait (test réel du 19/10/2026)."""
    clean = speech_text(text)
    if len(clean) <= limit:
        return clean, False
    head = clean[:limit]
    ends = [head.rfind(p) for p in (". ", "! ", "? ", "… ")]
    cut = max(ends)
    if cut >= limit // 3:
        return head[:cut + 1].strip(), True
    return head[:head.rfind(" ")].strip() + " …", True


def speech_text(text: str) -> str:
    """Texte à prononcer : sans Markdown (sinon la synthèse vocale lit les
    astérisques et les dièses des réponses du modèle, ex. "**3.14.8**").
    Une ligne (titre, puce, ligne de tableau) devient une phrase."""
    out = re.sub(r"```.*?```", " ", str(text or ""), flags=re.DOTALL)
    sentences = []
    for line in out.splitlines():
        line = line.replace("`", "").strip()      # accents graves isolés (transcription Gemini)
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
