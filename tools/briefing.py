"""Briefing du jour : date, météo, emails importants non lus, tâches planifiées.

Composé sans appel IA (0 token) : gui.py l'affiche de lui-même au premier
lancement de la journée (AMAH_BRIEFING=0 pour le désactiver), et "fais-moi le
point" le redonne à tout moment (tools/instant.py). Les trois sources sont
interrogées en parallèle (~3 s au lieu de ~6 s).
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
         "septembre", "octobre", "novembre", "décembre"]

_BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent.parent
_STATE = _BASE / "amah_state.json"


def _prenom() -> str:
    try:
        from config import _PRENOM
        return _PRENOM
    except Exception:
        return ""


def _weather_line() -> str:
    from tools.meteo import get_weather
    city = os.getenv("AMAH_CITY", "").strip() or "auto"
    w = get_weather(city)
    if not w.get("success"):
        return ""
    ville = w["ville"].split(",")[0]
    line = f"Météo à {ville} : {w['condition'].lower()}, {w['temperature']}"
    if w.get("previsions"):
        today = w["previsions"][0]
        line += f" (entre {today['min']} et {today['max']} aujourd'hui)"
    return line + "."


def _emails_line() -> str:
    from tools.email_watch import gmail_configured, important_unread
    if not gmail_configured():
        return ""
    mails = important_unread(days=3)
    if not mails:
        return "Aucun email important non lu."
    shown = [f"{m['de']} (« {m['sujet'][:60]} »)" for m in mails[:3]]
    more = f", et {len(mails) - 3} autre(s)" if len(mails) > 3 else ""
    s = "s" if len(mails) > 1 else ""
    return f"{len(mails)} email{s} important{s} non lu{s} : " + ", ".join(shown) + more + "."


def _tasks_line() -> str:
    from tools.scheduler import list_tasks
    res = list_tasks()
    tasks = res.get("taches") or []
    if not tasks:
        return ""
    names = [str(t.get("TaskName", "")).removeprefix("Amah_") for t in tasks]
    return "Tâches planifiées : " + ", ".join(n for n in names if n) + "."


def morning_briefing() -> dict:
    """Le point du jour, sans appel IA."""
    now = datetime.now()
    prenom = _prenom()
    hello = "Bonjour" if 5 <= now.hour < 18 else "Bonsoir"
    lines = [f"{hello}{' ' + prenom if prenom else ''} ! Nous sommes {_JOURS[now.weekday()]} "
             f"{now.day if now.day > 1 else '1er'} {_MOIS[now.month - 1]}, il est {now.hour} h {now:%M}."]
    sources = {"meteo": _weather_line, "emails": _emails_line, "taches": _tasks_line}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {name: pool.submit(fn) for name, fn in sources.items()}
    unavailable = []
    for name, future in futures.items():
        try:
            line = future.result()
        except Exception:
            unavailable.append(name)       # réseau coupé, Gmail refusé... : on saute
            continue
        if line:
            lines.append(line)
    return {"success": True, "texte": "\n".join(lines), "indisponible": unavailable}


# ── Une fois par jour ───────────────────────────────────────────────────────
def _read_state() -> dict:
    try:
        return json.loads(_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def briefing_due() -> bool:
    """Premier lancement de la journée (après 5 h) et briefing activé."""
    if os.getenv("AMAH_BRIEFING", "1").strip() == "0":
        return False
    if datetime.now().hour < 5:
        return False
    return _read_state().get("dernier_briefing") != date.today().isoformat()


def mark_briefing_done():
    state = _read_state()
    state["dernier_briefing"] = date.today().isoformat()
    try:
        _STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
