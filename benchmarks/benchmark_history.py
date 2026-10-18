"""Vérifie la conservation et la reprise de l'historique (tools/memory.py) — sans appel API.

Lancer depuis la racine du projet :
    py -3.13 -m benchmarks.benchmark_history

Travaille sur une base SQLite temporaire, jamais sur amah_memory.db.
Code de sortie 1 si une vérification échoue.
"""
import gc
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import tools.memory as M

results = []


def check(label, condition):
    results.append(bool(condition))
    print(("OK    " if condition else "ECHEC ") + label)


def ts(**delta):
    return (datetime.now() - timedelta(**delta)).strftime("%Y-%m-%d %H:%M:%S")


def insert(rows):
    with closing(sqlite3.connect(M.DB_PATH)) as conn, conn:
        conn.execute("DELETE FROM conversations")
        conn.executemany(
            "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?, ?, ?, ?)", rows)


def count():
    with closing(sqlite3.connect(M.DB_PATH)) as conn:
        return conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]


# ignore_cleanup_errors : tools/memory.py ouvre des connexions sans les fermer
# ("with sqlite3.connect()" valide mais ne ferme pas) ; Windows verrouille alors le fichier.
with tempfile.TemporaryDirectory(prefix="amah_history_", ignore_cleanup_errors=True) as tmp:
    real_db = M.DB_PATH
    M.DB_PATH = Path(tmp) / "test.db"
    M._connect().close()          # crée les tables
    saved_env = os.environ.pop("AMAH_HISTORY_DAYS", None)
    try:
        # 1. Durée de conservation
        check("défaut sans réglage : 365 jours", M.history_retention_days() == 365)
        for value, expected in (("0", 0), ("30", 30), ("abc", 365), ("-5", 0)):
            os.environ["AMAH_HISTORY_DAYS"] = value
            check(f"AMAH_HISTORY_DAYS={value!r} -> {expected}", M.history_retention_days() == expected)

        # 2. Nettoyage
        rows = [("old", "user", "vieux message", ts(days=400)), ("new", "user", "message récent", ts(days=10))]
        os.environ["AMAH_HISTORY_DAYS"] = "365"
        insert(rows); M.cleanup_old_messages()
        check("365 jours : message de 400 jours supprimé, récent gardé", count() == 1)
        os.environ["AMAH_HISTORY_DAYS"] = "0"
        insert(rows); M.cleanup_old_messages()
        check("Toujours (0) : rien n'est supprimé", count() == 2)

        # 3. Reprise au démarrage
        insert([
            ("s1", "user", "ancienne question", ts(hours=30)),
            ("s1", "assistant", "ancienne réponse", ts(hours=30)),
            ("s2", "user", "salut", ts(hours=1)),
            ("s2", "assistant", "Salut !", ts(hours=1)),
            ("s2", "user", "question restée sans réponse", ts(minutes=50)),
        ])
        resumed = M.load_resume_messages()
        check("session récente reprise, sans la question sans réponse",
              [m["content"] for m in resumed] == ["salut", "Salut !"])
        check("l'ancienne session n'est pas mélangée", all("ancienne" not in m["content"] for m in resumed))
        insert([("s1", "user", "question du 10 octobre", ts(days=8)),
                ("s1", "assistant", "réponse", ts(days=8))])
        check("dernière session de plus de 12 h : rien n'est repris", M.load_resume_messages() == [])
        insert([("s3", "user", "question sans réponse", ts(minutes=5))])
        check("session sans aucune réponse : rien n'est repris", M.load_resume_messages() == [])
    finally:
        gc.collect()
        M.DB_PATH = real_db
        os.environ.pop("AMAH_HISTORY_DAYS", None)
        if saved_env is not None:
            os.environ["AMAH_HISTORY_DAYS"] = saved_env

print(f"\n{sum(results)}/{len(results)} vérifications réussies")
sys.exit(0 if all(results) else 1)
