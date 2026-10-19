"""Journal de session lisible : ce qui se passe quand tu parles à Amah.

Activé par AMAH_JOURNAL=1 dans .env (désactivé par défaut). Écrit
amah_journal.txt à côté du programme — gitignoré : il contient tes
conversations. Pour chaque échange : ce que tu as dit (ou ce que Google a
entendu), ce qu'Amah a compris, chaque appel à l'IA (modèle, durée, tokens),
chaque outil (paramètres, résultat, durée), la réponse et le total.

    19:32:05  [voix] Tu as dit : « il fait quel temps à Paris »
              → outils proposés (intentions+mots) : get_weather_simple, get_weather
              · IA gpt-oss-120b : 1,8 s, 4 050 tokens
              · outil get_weather_simple(location='Paris') : 0,6 s → {"meteo": "Paris: +13°C"}
              · IA gpt-oss-120b : 1,6 s, 4 060 tokens
              ← Amah : « À Paris, il fait environ 13 °C. »   4,1 s · 2 appels IA · 8 110 tokens
"""
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

PATH = (Path(sys.executable).parent if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent.parent) / "amah_journal.txt"
_MAX_BYTES = 2_000_000
_lock = threading.Lock()
_turn = {"t0": None, "ia": 0, "tokens": 0}
_INDENT = " " * 10


def enabled() -> bool:
    return os.getenv("AMAH_JOURNAL", "0").strip() == "1"


def _write(line: str) -> None:
    try:
        with _lock:
            if PATH.exists() and PATH.stat().st_size > _MAX_BYTES:
                PATH.write_text(PATH.read_text(encoding="utf-8", errors="replace")[-_MAX_BYTES // 2:],
                                encoding="utf-8")
            with PATH.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass


def _short(value, limit: int = 140) -> str:
    if not isinstance(value, str):
        try:
            value = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            value = str(value)
    value = " ".join(value.split())
    return value if len(value) <= limit else value[:limit - 1] + "…"


def _secs(seconds: float) -> str:
    return f"{seconds:.1f} s".replace(".", ",")


def _num(n) -> str:
    return f"{n:,}".replace(",", " ")


def session(interface: str) -> None:
    """En-tête quand une interface démarre."""
    if enabled():
        _write(f"\n===== {interface} démarrée le {datetime.now():%d/%m/%Y à %H:%M:%S} =====")


def start(interface: str, text: str, spoken: bool = False) -> None:
    """Début d'un échange : la phrase de l'utilisateur."""
    if not enabled():
        return
    _turn.update(t0=time.time(), ia=0, tokens=0)
    who = "Tu as dit" if spoken else "Tu as écrit"
    _write(f"\n{datetime.now():%H:%M:%S}  [{interface}] {who} : « {_short(text, 300)} »")


def note(text: str) -> None:
    """Ce qu'Amah a compris (réponse instantanée, mémoire, outils proposés…)."""
    if enabled():
        _write(f"{_INDENT}→ {text}")


def routing(tools, info=None) -> None:
    """Décision du routeur d'outils."""
    if not enabled():
        return
    names = [t["function"]["name"] for t in (tools or [])]
    if not names:
        note("conversation : aucun outil (prompt court)")
        return
    level = f" ({info.get('niveau')})" if isinstance(info, dict) and info.get("niveau") else ""
    more = f" … ({len(names)} en tout)" if len(names) > 6 else ""
    note(f"outils proposés{level} : {', '.join(names[:6])}{more}")


def ia(model: str, seconds: float, tokens=None) -> None:
    """Un appel au modèle."""
    if not enabled():
        return
    _turn["ia"] += 1
    if tokens:
        _turn["tokens"] += tokens
    used = f", {_num(tokens)} tokens" if tokens else ""
    _write(f"{_INDENT}· IA {str(model).split('/')[-1]} : {_secs(seconds)}{used}")


def tool(name: str, args: dict, result, seconds: float) -> None:
    """Un outil exécuté (ou refusé)."""
    if not enabled():
        return
    shown_args = ", ".join(f"{k}={_short(v, 50)!r}" if isinstance(v, str) else f"{k}={_short(v, 50)}"
                           for k, v in (args or {}).items())
    refused = isinstance(result, dict) and result.get("refuse")
    outcome = "REFUSÉ par l'utilisateur" if refused else _short(result)
    _write(f"{_INDENT}· outil {name}({shown_args}) : {_secs(seconds)} → {outcome}")


def end(reply: str, error: bool = False) -> None:
    """Réponse d'Amah et total de l'échange."""
    if not enabled():
        return
    total = _secs(time.time() - _turn["t0"]) if _turn["t0"] else ""
    parts = [total] if total else []
    if _turn["ia"]:
        parts.append(f"{_turn['ia']} appel{'s' if _turn['ia'] > 1 else ''} IA")
    else:
        parts.append("sans IA")
    if _turn["tokens"]:
        parts.append(f"{_num(_turn['tokens'])} tokens")
    label = "ERREUR" if error else "Amah"
    _write(f"{_INDENT}← {label} : « {_short(reply, 300)} »   {' · '.join(parts)}")
    _turn["t0"] = None


def wake(heard: str, woke: bool) -> None:
    """Mot de réveil : ce que le micro a entendu."""
    if not enabled():
        return
    if not heard:
        _write(f"{datetime.now():%H:%M:%S}  [réveil] son capté, Google n'a rien compris")
        return
    verdict = "Amah se réveille" if woke else "ce n'est pas le mot de réveil"
    _write(f"{datetime.now():%H:%M:%S}  [réveil] entendu « {_short(heard, 120)} » → {verdict}")
