import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta

log = logging.getLogger("amah.memory")

if getattr(sys, 'frozen', False):
    DB_PATH = Path(sys.executable).parent / "amah_memory.db"
else:
    DB_PATH = Path(__file__).parent.parent / "amah_memory.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            category   TEXT    NOT NULL DEFAULT 'general',
            content    TEXT    NOT NULL,
            created_at TEXT    NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT    NOT NULL,
            role       TEXT    NOT NULL,
            content    TEXT    NOT NULL,
            created_at TEXT    NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_message(session_id: str, role: str, content: str) -> None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
    except Exception as e:
        log.warning("save_message failed: %s", e)


def cleanup_old_messages(days: int = 90) -> None:
    """Supprime les messages de conversation de plus de X jours."""
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM conversations WHERE created_at < ?", (cutoff,))
    except Exception as e:
        log.warning("cleanup_old_messages failed: %s", e)


def load_recent_messages(limit: int = 20) -> list:
    try:
        conn = _connect()
        rows = conn.execute(
            "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception as e:
        log.warning("load_recent_messages failed: %s", e)
        return []


def save_memory(content: str, category: str = "general") -> dict:
    try:
        conn = _connect()
        conn.execute(
            "INSERT INTO memories (category, content, created_at) VALUES (?, ?, ?)",
            (category, content, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": f"Mémorisé dans '{category}' : {content}"}
    except Exception as e:
        return {"error": str(e)}


def get_memories(category: str = None) -> dict:
    try:
        conn = _connect()
        if category:
            rows = conn.execute(
                "SELECT id, category, content, created_at FROM memories WHERE category=? ORDER BY id DESC LIMIT 30",
                (category,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, category, content, created_at FROM memories ORDER BY id DESC LIMIT 30"
            ).fetchall()
        conn.close()
        memories = [{"id": r[0], "categorie": r[1], "contenu": r[2], "date": r[3]} for r in rows]
        return {"success": True, "total": len(memories), "memories": memories}
    except Exception as e:
        return {"error": str(e)}


def delete_memory(memory_id: int) -> dict:
    try:
        conn = _connect()
        conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        conn.commit()
        conn.close()
        return {"success": True, "message": f"Mémoire #{memory_id} supprimée"}
    except Exception as e:
        return {"error": str(e)}
