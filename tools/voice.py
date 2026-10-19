import asyncio
import os
import tempfile
import threading
from concurrent.futures import Future

VOICE = "fr-FR-HenriNeural"

_stopped = threading.Event()  # posé par stop_voice : interruption volontaire


async def _generate_tts(text: str, rate: str):
    """Génère le MP3 avec edge-tts : (chemin, fin de la parole en ms ou None).

    edge-tts ajoute du silence après la phrase (1,87 s d'audio pour "Oui.",
    parole finie à 1,23 s) : la lecture s'arrête à la fin de la parole."""
    import edge_tts   # ~1,3 s : chargé à la première parole, plus au démarrage d'Amah
    tts = edge_tts.Communicate(text, voice=VOICE, rate=rate)
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        speech_end = None
        with open(path, "wb") as f:
            async for chunk in tts.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif "offset" in chunk and "duration" in chunk:
                    # Unités de 100 ns -> millisecondes
                    speech_end = (chunk["offset"] + chunk["duration"]) / 10_000
        return path, speech_end
    except Exception:
        try:
            os.unlink(path)
        except Exception:
            pass
        raise


async def _generate_tts_with_timeout(text: str, rate: str) -> str:
    """Wrapper async unique : le timeout vit dans la même coroutine."""
    return await asyncio.wait_for(_generate_tts(text, rate), timeout=10)


def _run_async_safely(coro_factory):
    """Exécute une coroutine sans conflit avec la boucle async du thread appelant.

    - Sans boucle active : asyncio.run() directement.
    - Avec une boucle active : exécute asyncio.run() dans un thread dédié.

    La coroutine n'est créée qu'au dernier moment, donc aucune coroutine
    temporaire ne reste non attendue en cas d'exception.
    """
    try:
        asyncio.get_running_loop()
        running = True
    except RuntimeError:
        running = False

    if not running:
        return asyncio.run(coro_factory())

    result_future: Future = Future()

    def worker():
        try:
            result_future.set_result(asyncio.run(coro_factory()))
        except BaseException as exc:
            result_future.set_exception(exc)

    thread = threading.Thread(target=worker, name="amah-tts", daemon=True)
    thread.start()
    return result_future.result()


def speak(text: str, speed: int = 2, on_start=None) -> dict:
    """Fait parler Amah avec SA voix, Henri (edge-tts, fr-FR), partout : réponses
    de l'interface vocale, lecture de pages, fenêtre. Sans Internet : voix
    Windows en repli. Bloquant jusqu'à la fin de la phrase (ou stop_voice).

    Avant : deux voix se mélangeaient (Henri pour la lecture, la voix Windows
    Hortense pour les réponses vocales) et Henri était joué par un PowerShell
    lancé à chaque phrase (plusieurs secondes de démarrage). Il est maintenant
    joué directement par Amah (Windows MCI), sans PowerShell.
    """
    original = str(text or "")
    safe = original.replace('"', ' ').replace("'", ' ').replace('\n', ' ').strip()
    if not safe:
        return {"error": "Texte vide à lire."}

    def started():
        # on_start : appelé quand le son démarre, pour afficher le texte au
        # même moment (Henri met ~1,5 s à préparer sa voix)
        if on_start:
            try:
                on_start()
            except Exception:
                pass

    try:
        level = int(speed)
    except (TypeError, ValueError):
        level = 2
    rate = f"+{max(-50, min(50, level * 5))}%"
    _stopped.clear()
    interrupted = {"success": True, "dit": original[:120], "interrompu": True}

    for attempt in range(2):
        path = None
        try:
            path, speech_end = _run_async_safely(lambda: _generate_tts_with_timeout(safe, rate))
            if _stopped.is_set():
                return interrupted
            started()
            _play_mp3(path, speech_end)
            if _stopped.is_set():
                return {**interrupted, "voice": "Henri"}
            return {"success": True, "dit": original[:120], "voice": "Henri"}
        except Exception:
            if _stopped.is_set():
                return interrupted
        finally:
            if path:
                try:
                    os.unlink(path)
                except Exception:
                    pass

    # Repli hors ligne : voix Windows, appelée directement (pas de PowerShell,
    # donc aucun texte inséré dans un script — voir benchmark_injection)
    try:
        started()
        _sapi_speak(safe, level)
        if _stopped.is_set():
            return interrupted
        return {"success": True, "dit": original[:120], "voice": "Windows (hors ligne)"}
    except Exception as e:
        return {"error": f"Voix indisponible : {e}"}


def _mci(command: str):
    """Commande Windows MCI (lecture audio dans le processus)."""
    import ctypes
    buffer = ctypes.create_unicode_buffer(256)
    error = ctypes.windll.winmm.mciSendStringW(command, buffer, 255, 0)
    return error, buffer.value


def _play_mp3(path: str, speech_end_ms=None) -> None:
    """Joue le MP3 jusqu'à la fin de la parole (ou jusqu'à stop_voice). Lève une
    erreur si Windows ne peut pas le lire."""
    alias = f"amah_voix_{threading.get_ident()}"
    error, _ = _mci(f'open "{os.path.abspath(path)}" type mpegvideo alias {alias}')
    if error:
        raise RuntimeError(f"Lecture audio impossible (MCI {error})")
    try:
        _mci(f"set {alias} time format milliseconds")
        until = f" from 0 to {int(speech_end_ms) + 150}" if speech_end_ms else ""
        error, _ = _mci(f"play {alias}{until}")
        if error and until:
            error, _ = _mci(f"play {alias}")       # fin hors limites : tout lire
        if error:
            raise RuntimeError(f"Lecture audio impossible (MCI {error})")
        while not _stopped.is_set():
            error, mode = _mci(f"status {alias} mode")
            if error or mode != "playing":
                break
            _stopped.wait(0.05)
        if _stopped.is_set():
            _mci(f"stop {alias}")
    finally:
        _mci(f"close {alias}")


def _sapi_speak(text: str, level: int = 2) -> None:
    """Voix Windows (SAPI) dans ce fil, interruptible par stop_voice."""
    import comtypes
    import comtypes.client
    comtypes.CoInitialize()
    voice = comtypes.client.CreateObject("SAPI.SpVoice")
    voices = voice.GetVoices()
    for i in range(voices.Count):
        token = voices.Item(i)
        if any(k in token.GetDescription().lower() for k in ("french", "français", "francais", "hortense")):
            voice.Voice = token
            break
    voice.Rate = max(-10, min(10, level))
    voice.Speak(text, 1)                      # asynchrone : on peut couper
    while not voice.WaitUntilDone(100):
        if _stopped.is_set():
            voice.Speak("", 1 | 2)            # purge : coupe la phrase en cours
            break


def stop_voice() -> dict:
    """Coupe la voix en cours (Henri ou voix Windows)."""
    _stopped.set()
    return {"success": True}


# ── Mode Live : Henri lit un texte qui arrive par morceaux ──────────────────
import queue as _queue
import re as _re
import time as _time

# Fin de phrase = ponctuation SUIVIE d'un espace. Avant, une phrase était
# "tout sauf un point, puis un point" : le point de "campusmarket-nu.vercel.app"
# coupait la phrase et tout le texte d'avant était perdu (test du 19/10/2026).
_SENTENCE_END = _re.compile(r"[.!?…]+[»\")]*(?=\s)")


class SentenceSpeaker:
    """Fait dire par Henri un texte qui arrive par morceaux (transcription des
    réponses de Gemini Live) : découpe en phrases, prépare la phrase suivante
    pendant que la courante est jouée (pas de blanc de ~1,5 s entre les
    phrases), et s'arrête net sur interrupt().

    speaking (threading.Event, facultatif) est posé tant qu'Henri parle (et
    0,35 s après) : le mode Live coupe alors le micro pour ne pas renvoyer la
    voix d'Amah à Gemini comme si l'utilisateur parlait."""

    HANGOVER = 0.35
    MAX_PENDING = 180          # texte sans ponctuation : on coupe quand même

    def __init__(self, speaking=None, rate: str = "+10%", on_start=None):
        self.speaking = speaking
        self.rate = rate
        self.on_start = on_start          # on_start(phrase, tag) quand elle est dite
        self.tag = 0                      # numéro de réponse (affichage par réponse)
        self._buffer = ""
        self._generation = 0
        self._texts = _queue.Queue()
        self._audio = _queue.Queue()
        self._pending = 0              # phrases en préparation ou à jouer
        self._lock = threading.Lock()
        self._closed = False
        threading.Thread(target=self._prepare_loop, name="henri-prepare", daemon=True).start()
        threading.Thread(target=self._play_loop, name="henri-play", daemon=True).start()

    # -- entrée ---------------------------------------------------------
    def feed(self, chunk: str) -> None:
        """Ajoute un morceau de texte ; les phrases complètes partent à Henri."""
        self._buffer += str(chunk or "")
        sentences = []
        consumed = 0
        for m in _SENTENCE_END.finditer(self._buffer):
            sentences.append(self._buffer[consumed:m.end()])
            consumed = m.end()
        rest = self._buffer[consumed:]
        if len(rest) > self.MAX_PENDING:
            cut = max(rest.rfind(", ", 0, self.MAX_PENDING), rest.rfind(" ", 0, self.MAX_PENDING))
            if cut > 40:
                sentences.append(rest[:cut + 1])
                rest = rest[cut + 1:]
        self._buffer = rest
        for s in sentences:
            self._say(s)

    def flush(self) -> None:
        """Fin de la réponse : dit ce qui reste."""
        rest, self._buffer = self._buffer, ""
        self._say(rest)

    def interrupt(self) -> None:
        """Coupe tout : phrase en cours et phrases à venir."""
        with self._lock:
            self._generation += 1
            self._buffer = ""
            for q in (self._texts, self._audio):
                while True:
                    try:
                        item = q.get_nowait()
                    except _queue.Empty:
                        break
                    if q is self._audio and item and item[1]:      # (gen, chemin, …)
                        try:
                            os.unlink(item[1])
                        except Exception:
                            pass
            self._pending = 0
        _stopped.set()                  # arrête la lecture MCI en cours

    def close(self) -> None:
        self.interrupt()
        self._closed = True
        self._texts.put(None)
        self._audio.put(None)

    def busy(self) -> bool:
        return self._pending > 0

    # -- interne --------------------------------------------------------
    def _say(self, text: str) -> None:
        from tools.conversation import speech_text
        text = speech_text(text).replace('"', " ").strip()
        if not text:
            return
        with self._lock:
            self._pending += 1
            if self.speaking is not None:
                self.speaking.set()
            self._texts.put((self._generation, text, self.tag))

    def _prepare_loop(self):
        while True:
            item = self._texts.get()
            if item is None:
                return
            gen, text, tag = item
            if gen != self._generation:
                continue
            try:
                path, end = _run_async_safely(lambda: _generate_tts_with_timeout(text, self.rate))
                self._audio.put((gen, path, end, None, text, tag))
            except Exception:
                self._audio.put((gen, None, None, text, text, tag))   # repli : voix Windows

    def _play_loop(self):
        while True:
            item = self._audio.get()
            if item is None:
                return
            gen, path, end, fallback_text, text, tag = item
            try:
                if gen == self._generation:
                    _stopped.clear()
                    if self.on_start:
                        try:
                            self.on_start(text, tag)
                        except Exception:
                            pass
                    if path:
                        _play_mp3(path, end)
                    elif fallback_text:
                        _sapi_speak(fallback_text)
            except Exception:
                pass
            finally:
                if path:
                    try:
                        os.unlink(path)
                    except Exception:
                        pass
                with self._lock:
                    if gen == self._generation and self._pending > 0:
                        self._pending -= 1
                    idle = self._pending == 0
                if idle and self.speaking is not None:
                    _time.sleep(self.HANGOVER)
                    if self._pending == 0:
                        self.speaking.clear()
