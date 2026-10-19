"""Tes vraies phrases, tirées de l'historique d'Amah : ce qu'Amah en comprend
aujourd'hui (réponse instantanée, mémoire, conversation, outils proposés),
comparé au comportement attendu — sans appel IA, sans réseau.

Les phrases et le comportement attendu sont dans benchmarks/mes_conversations.json,
un fichier LOCAL (gitignoré, comme user_profile.txt) : il contient des
conversations personnelles et ne doit jamais être publié. Ce script n'en
contient aucune.

Lancer depuis la racine du projet :
    py -3.13 -m benchmarks.benchmark_mes_conversations
    py -3.13 -m benchmarks.benchmark_mes_conversations --extraire
        ajoute les nouvelles phrases de amah_memory.db à étiqueter
        ("attendu": "a_etiqueter"), sans toucher aux étiquettes existantes

Comportement attendu ("attendu"), plusieurs conditions séparées par ";" :
    conversation        aucun outil (prompt court, le moins cher)
    instant:<type>      réponse sans IA : heure, calcul, briefing, lecture, arret
    memoire             rappel de mémoire, ou get_memories proposé
    quitte              (interface vocale) la phrase ferme l'interface
    outil:a|b           a ou b fait partie des outils proposés au modèle
    pas:a|b             ni a ni b ne sont proposés
    pas_impose          aucun outil imposé (pas de web_search forcé)
    ignore:<raison>     exclu du score (dépend du message précédent…)
Code de sortie 1 si une phrase évaluée échoue.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

DATA = Path(__file__).with_name("mes_conversations.json")


def analyse(text: str, voice: bool) -> dict:
    """Ce qu'Amah fait de la phrase, sans appel IA ni effet de bord."""
    import voice_fullscreen as V
    from config import TOOLS_DEFINITIONS
    from tools.fastpath_v01 import _extract_calculation, normalize_text
    from tools.instant import _ALOUD, _BRIEFING, _STOP_READING, _URL, datetime_request_kind
    from tools.memory_context import memory_context
    from tools.tool_router import forced_tool, normalize, select_tools

    r = {"instant": None, "quitte": False, "memoire": False, "outils": [], "impose": None}
    if voice and V._is_quit_request(text):
        r["quitte"] = True
        return r
    n = normalize(text)
    if _STOP_READING.match(text.strip()):
        r["instant"] = "arret"
    elif _ALOUD.search(n) and _URL.search(text):
        r["instant"] = "lecture"
    elif _BRIEFING.match(n):
        r["instant"] = "briefing"
    elif datetime_request_kind(text):
        r["instant"] = "heure"
    elif _extract_calculation(normalize_text(text)):
        r["instant"] = "calcul"
    if r["instant"]:
        return r
    try:
        res, _direct = memory_context(text, summarize_fn=lambda p: (_ for _ in ()).throw(RuntimeError()))
        r["memoire"] = res is not None
    except Exception:
        pass
    tools, info = select_tools(text, TOOLS_DEFINITIONS)
    r["outils"] = [t["function"]["name"] for t in tools]
    if tools:
        r["impose"] = forced_tool(text, tools, info)
    return r


def satisfied(expect: str, r: dict) -> bool:
    for cond in expect.split(";"):
        cond = cond.strip()
        kind, _, arg = cond.partition(":")
        options = arg.split("|") if arg else []
        ok = {
            "conversation": lambda: not r["instant"] and not r["memoire"] and not r["outils"] and not r["quitte"],
            "instant": lambda: r["instant"] in options,
            "memoire": lambda: r["memoire"] or "get_memories" in r["outils"],
            "quitte": lambda: r["quitte"],
            "outil": lambda: any(o in r["outils"] for o in options),
            "pas": lambda: not any(o in r["outils"] for o in options),
            "pas_impose": lambda: r["impose"] is None,
        }[kind]()
        if not ok:
            return False
    return True


def describe(r: dict) -> str:
    if r["quitte"]:
        return "ferme l'interface"
    if r["instant"]:
        return f"réponse instantanée ({r['instant']})"
    parts = ["rappel de mémoire"] if r["memoire"] else []
    parts.append(f"outils : {', '.join(r['outils'][:5])}" + ("…" if len(r["outils"]) > 5 else "")
                 if r["outils"] else "conversation (aucun outil)")
    if r["impose"]:
        parts.append(f"{r['impose']} imposé")
    return " | ".join(parts)


def extract():
    """Ajoute les phrases de l'historique absentes du fichier, à étiqueter."""
    from tools.memory import DB_PATH
    data = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"cas": []}
    known = {re.sub(r"\s+", " ", c["phrase"].strip().lower()) for c in data["cas"]}
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT session_id, content, MIN(created_at) FROM conversations WHERE role='user' "
                        "GROUP BY lower(trim(content)) ORDER BY MIN(created_at)").fetchall()
    conn.close()
    added = 0
    for session, text, when in rows:
        key = re.sub(r"\s+", " ", text.strip().lower())
        if key in known or session in ("banc", "audit"):
            continue
        voice = session.startswith("voix")
        data["cas"].append({"phrase": text, "voix": voice, "date": when[:10], "attendu": "a_etiqueter",
                            "aujourd_hui": describe(analyse(text, voice))})
        known.add(key)
        added += 1
    data.setdefault("_info", "Fichier LOCAL (gitignoré) : conversations personnelles, ne jamais le publier.")
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{added} nouvelle(s) phrase(s) à étiqueter dans {DATA.name}")


def main():
    if "--extraire" in sys.argv:
        extract()
        return 0
    if not DATA.exists():
        print(f"{DATA.name} introuvable : lance d'abord --extraire puis étiquette les phrases.")
        return 1
    cases = json.loads(DATA.read_text(encoding="utf-8"))["cas"]
    scored = [c for c in cases if not c["attendu"].startswith(("ignore", "a_etiqueter"))]
    failures = []
    for c in scored:
        r = analyse(c["phrase"], c["voix"])
        if not satisfied(c["attendu"], r):
            failures.append((c, r))
    todo = sum(c["attendu"] == "a_etiqueter" for c in cases)
    print(f"{len(cases)} phrases réelles : {len(scored)} évaluées, "
          f"{len(cases) - len(scored) - todo} ignorées (ambiguës), {todo} à étiqueter\n")
    for c, r in failures:
        flat = re.sub(r"\s+", " ", c["phrase"])
        print(f"ÉCHEC {'[voix] ' if c['voix'] else ''}« {flat[:80]} »")
        print(f"      attendu : {c['attendu']}\n      obtenu  : {describe(r)}")
    print(f"\n{len(scored) - len(failures)}/{len(scored)} phrases réelles bien comprises")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
