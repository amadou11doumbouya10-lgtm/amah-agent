import os
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


DEFAULT_HISTORY_DAYS = 365


def history_retention_days() -> int:
    """Durée de conservation des conversations choisie par l'utilisateur.

    AMAH_HISTORY_DAYS dans .env (écran de configuration) ; 0 = toujours garder.
    Le rappel de mémoire (tools/memory_context.py) cherche dans cet historique :
    une durée trop courte efface ce qu'Amah pourrait retrouver.
    """
    try:
        days = int(os.getenv("AMAH_HISTORY_DAYS", "").strip() or DEFAULT_HISTORY_DAYS)
    except ValueError:
        days = DEFAULT_HISTORY_DAYS
    return max(0, days)


def cleanup_old_messages(days: int = None) -> None:
    """Supprime les messages de conversation plus anciens que la durée choisie."""
    if days is None:
        days = history_retention_days()
    if days <= 0:
        return  # conservation illimitée
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM conversations WHERE created_at < ?", (cutoff,))
    except Exception as e:
        log.warning("cleanup_old_messages failed: %s", e)


def truncate_old_tool_results(max_chars: int = 800) -> None:
    """Tronque rétroactivement les tool_results trop longs dans la DB."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id, content FROM conversations WHERE role='tool' AND length(content) > ?",
                (max_chars,)
            ).fetchall()
            for row_id, content in rows:
                truncated = content[:max_chars] + "...[tronque]"
                conn.execute("UPDATE conversations SET content=? WHERE id=?", (truncated, row_id))
            if rows:
                log.warning("truncate_old_tool_results: %d messages tronques", len(rows))
    except Exception as e:
        log.warning("truncate_old_tool_results failed: %s", e)


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


def load_resume_messages(max_age_hours: float = 12, limit: int = 10) -> list:
    """Messages à reprendre au démarrage : la dernière session seulement, si
    elle est récente, sans question restée sans réponse à la fin.

    load_recent_messages() rechargeait les 10 derniers messages quelle que soit
    leur date : une question du 10 octobre restée sans réponse a été prise le
    18 pour la demande en cours ("salut" -> description d'écran inventée).
    """
    try:
        conn = _connect()
        last = conn.execute(
            "SELECT session_id, created_at FROM conversations ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not last:
            conn.close()
            return []
        session_id, last_at = last
        try:
            age = datetime.now() - datetime.strptime(str(last_at)[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            age = timedelta(days=9999)
        if age > timedelta(hours=max_age_hours):
            conn.close()
            return []
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? "
            "AND role IN ('user', 'assistant') ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        conn.close()
        messages = [{"role": r[0], "content": r[1]} for r in reversed(rows)]
        while messages and messages[-1]["role"] != "assistant":
            messages.pop()           # question sans réponse : ne pas la reposer
        while messages and messages[0]["role"] != "user":
            messages.pop(0)          # commencer par l'utilisateur
        return messages
    except Exception as e:
        log.warning("load_resume_messages failed: %s", e)
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
            # Le modèle passe souvent un sujet ("couleur préférée") au lieu
            # d'une catégorie ("preferences") : chercher aussi dans le contenu,
            # puis tout renvoyer plutôt que répondre "aucun souvenir" à tort.
            rows = conn.execute(
                "SELECT id, category, content, created_at FROM memories "
                "WHERE category = ? OR (category != 'conversation_summary' AND content LIKE ?) "
                "ORDER BY id DESC LIMIT 30",
                (category, f"%{category}%")
            ).fetchall()
            if not rows:
                rows = conn.execute(
                    "SELECT id, category, content, created_at FROM memories "
                    "WHERE category != 'conversation_summary' ORDER BY id DESC LIMIT 30"
                ).fetchall()
        else:
            # Les résumés JSON mis en cache par le rappel de mémoire (V0.2.4) ne
            # sont pas des souvenirs de l'utilisateur : ne pas les lui afficher.
            rows = conn.execute(
                "SELECT id, category, content, created_at FROM memories "
                "WHERE category != 'conversation_summary' ORDER BY id DESC LIMIT 30"
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
