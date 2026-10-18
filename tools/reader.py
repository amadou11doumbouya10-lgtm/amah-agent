"""Lecture complète d'une page web à voix haute, en arrière-plan.

Avant, "lis-moi cette page" passait par le modèle : il ne voyait que les 2 000
premiers caractères du résultat (souvent le menu du site) et n'en lisait
qu'un résumé. Ici, le texte principal de la page est lu en entier par
morceaux, sans appel IA ; "arrête la lecture" coupe tout de suite
(tools/instant.py, sans appel IA non plus).
"""
import atexit
import re
import threading

_thread = None
_stop = threading.Event()
_lock = threading.Lock()
_state = {"titre": "", "lus": 0, "total": 0}

# ~150 mots/minute pour la voix Henri à +10 %
_CHARS_PER_MINUTE = 900
_CHUNK = 600


def is_reading() -> bool:
    return _thread is not None and _thread.is_alive()


def _chunks(text: str, size: int = _CHUNK) -> list:
    """Morceaux de ~size caractères, coupés entre deux phrases.

    Un morceau court se synthétise vite (edge-tts a un délai de 10 s par appel)
    et la lecture peut s'arrêter entre deux morceaux."""
    pieces = [p.strip() for p in re.split(r"(?<=[.!?…:;])\s+|\n+", text) if p.strip()]
    chunks, current = [], ""
    for piece in pieces:
        while len(piece) > size:              # phrase démesurée (liste sans point)
            cut = piece.rfind(" ", 0, size)
            cut = cut if cut > size // 2 else size
            head, piece = piece[:cut], piece[cut:].strip()
            if current:
                chunks.append(current)
                current = ""
            chunks.append(head)
        if current and len(current) + 1 + len(piece) > size:
            chunks.append(current)
            current = piece
        else:
            current = f"{current} {piece}".strip()
    if current:
        chunks.append(current)
    return chunks


def _worker(chunks):
    from tools.voice import speak
    for i, chunk in enumerate(chunks):
        if _stop.is_set():
            break
        speak(chunk)
        _state["lus"] = i + 1


def stop_reading() -> dict:
    """Arrête la lecture en cours (sans effet si rien n'est lu)."""
    if not is_reading():
        return {"success": True, "info": "Aucune lecture en cours."}
    _stop.set()
    try:
        from tools.voice import stop_voice
        stop_voice()
    except Exception:
        pass
    if _thread is not None:
        _thread.join(timeout=3)
    return {"success": True, "info": "Lecture arrêtée.", "titre": _state["titre"],
            "morceaux_lus": _state["lus"], "morceaux_total": _state["total"]}


# Fermer Amah coupe aussi la voix (sinon le morceau en cours continue seul)
atexit.register(lambda: stop_reading() if is_reading() else None)


def _page_text(url: str) -> dict:
    """Texte complet : URL donnée (requête simple, puis navigateur si le site
    refuse ou se construit en JavaScript), sinon la page ouverte dans le navigateur."""
    if url:
        if not re.match(r"https?://", url, re.I):
            url = "https://" + url
        try:
            from tools.search import fetch_main_text
            page = fetch_main_text(url)
            if len(page["texte"]) >= 200:
                return page
        except Exception:
            pass
        from tools.browser import open_and_read
        return open_and_read(url)
    from tools.browser import current_page_main_text
    page = current_page_main_text()
    if page is None:
        raise ValueError("Aucune page ouverte : donne l'adresse de la page à lire, "
                         "ou ouvre-la d'abord avec open_browser.")
    return page


def read_aloud(url: str = "", stop: bool = False) -> dict:
    """Lit à voix haute TOUT le contenu principal d'une page web, en arrière-plan.

    url  : page à lire ; vide = page ouverte dans le navigateur.
    stop : True pour arrêter la lecture en cours.
    """
    global _thread
    if stop:
        return stop_reading()
    try:
        page = _page_text(str(url or "").strip())
    except Exception as e:
        return {"error": str(e)}
    text = page.get("texte", "").strip()
    if len(text) < 40:
        return {"error": "Je n'ai pas trouvé de texte à lire sur cette page."}

    with _lock:
        if is_reading():
            stop_reading()
        chunks = _chunks(text)
        _stop.clear()
        _state.update(titre=page.get("titre", ""), lus=0, total=len(chunks))
        _thread = threading.Thread(target=_worker, args=(chunks,), name="amah-lecture", daemon=True)
        _thread.start()

    minutes = max(1, round(len(text) / _CHARS_PER_MINUTE))
    return {
        "success": True,
        "info": "Lecture à voix haute lancée en arrière-plan. Ne relis pas le texte "
                "toi-même ; dis à l'utilisateur qu'il peut dire « arrête la lecture ».",
        "titre": page.get("titre", ""),
        "url": page.get("url", url),
        "caracteres": len(text),
        "duree_estimee_minutes": minutes,
        "debut": text[:300],
    }
