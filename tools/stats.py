"""
Statistiques d'utilisation d'Amah — stockées dans amah_memory.db.
"""
import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger("amah.stats")

if getattr(sys, 'frozen', False):
    DB_PATH = Path(sys.executable).parent / "amah_memory.db"
else:
    DB_PATH = Path(__file__).parent.parent / "amah_memory.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tool_usage (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name  TEXT NOT NULL,
            used_at    TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def record_tool_use(tool_name: str) -> None:
    """Enregistre l'utilisation d'un outil (appelé en interne)."""
    try:
        conn = _connect()
        conn.execute(
            "INSERT INTO tool_usage (tool_name, used_at) VALUES (?, ?)",
            (tool_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.debug(f"Enregistrement de l'usage de l'outil '{tool_name}' ignore : {e}")


def get_stats(days: int = 30) -> dict:
    """Retourne les statistiques d'utilisation des outils sur les X derniers jours."""
    try:
        conn = _connect()
        rows = conn.execute("""
            SELECT tool_name, COUNT(*) as utilisations
            FROM tool_usage
            WHERE used_at >= datetime('now', ? || ' days')
            GROUP BY tool_name
            ORDER BY utilisations DESC
        """, (f"-{days}",)).fetchall()

        total = conn.execute("""
            SELECT COUNT(*) FROM tool_usage
            WHERE used_at >= datetime('now', ? || ' days')
        """, (f"-{days}",)).fetchone()[0]

        sessions = conn.execute("""
            SELECT COUNT(DISTINCT date(used_at)) FROM tool_usage
            WHERE used_at >= datetime('now', ? || ' days')
        """, (f"-{days}",)).fetchone()[0]

        conn.close()

        tools = [{"outil": r[0], "utilisations": r[1]} for r in rows]
        return {
            "success":      True,
            "periode":      f"{days} derniers jours",
            "total_appels": total,
            "sessions":     sessions,
            "top_outils":   tools[:10],
        }
    except Exception as e:
        return {"error": str(e)}


def reset_stats() -> dict:
    """Efface toutes les statistiques d'utilisation."""
    try:
        conn = _connect()
        conn.execute("DELETE FROM tool_usage")
        conn.commit()
        conn.close()
        return {"success": True, "message": "Statistiques effacees"}
    except Exception as e:
        return {"error": str(e)}
