import asyncio
import os
import subprocess
import tempfile
import threading
from concurrent.futures import Future

import edge_tts

VOICE = "fr-FR-HenriNeural"

_ps_proc = None  # processus PowerShell de lecture en cours (pour stop_voice)
_stopped = threading.Event()  # pose par stop_voice : interruption volontaire


async def _generate_tts(text: str, rate: str) -> str:
    """Génère le MP3 avec edge-tts et retourne son chemin."""
    tts = edge_tts.Communicate(text, voice=VOICE, rate=rate)
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        await tts.save(path)
        return path
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


def speak(text: str, speed: int = 2) -> dict:
    """Synthèse vocale via edge-tts avec fallback Windows TTS.

    Version V0.3 : exécution async robuste, compatible avec ou sans boucle
    asyncio déjà active dans le thread appelant.
    """
    global _ps_proc
    original = str(text or "")
    safe = original.replace('"', ' ').replace("'", ' ').replace('\n', ' ').strip()
    if not safe:
        return {"error": "Texte vide à lire."}

    rate = f"+{max(-50, min(50, speed * 5))}%"
    _stopped.clear()

    for attempt in range(2):
        path = None
        try:
            path = _run_async_safely(
                lambda: _generate_tts_with_timeout(safe, rate)
            )

            proc = _ps_proc = play_mp3_blocking(path)
            returncode = proc.wait()  # copie locale : stop_voice() remet _ps_proc a None
            _ps_proc = None
            if _stopped.is_set():
                # Coupure volontaire : ne pas relire ni basculer sur le TTS Windows
                return {"success": True, "dit": original[:120], "voice": "Henri", "interrompu": True}
            if returncode not in (0, None):
                raise RuntimeError(f"Lecture audio échouée (code {returncode})")

            return {"success": True, "dit": original[:120], "voice": "Henri"}
        except Exception:
            if _ps_proc is not None:
                try:
                    if _ps_proc.poll() is None:
                        _ps_proc.terminate()
                except Exception:
                    pass
                _ps_proc = None
            if _stopped.is_set():
                return {"success": True, "dit": original[:120], "interrompu": True}
            if attempt == 0:
                continue
        finally:
            if path:
                try:
                    os.unlink(path)
                except Exception:
                    pass

    # Fallback Windows TTS (hors ligne)
    try:
        # Texte passé par variable d'environnement, jamais dans le code du
        # script : PowerShell traite aussi “ ” „ comme des guillemets, et un
        # texte piégé (page lue par read_aloud) exécutait du code (testé).
        try:
            rate = int(max(-10, min(10, int(speed))))
        except (TypeError, ValueError):
            rate = 2
        ps = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Rate = [int]$env:AMAH_TTS_RATE; "
            "$s.Speak($env:AMAH_TTS_TEXT);"
        )
        if _stopped.is_set():
            return {"success": True, "dit": original[:120], "interrompu": True}
        proc = _ps_proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "AMAH_TTS_TEXT": safe, "AMAH_TTS_RATE": str(rate)},
        )
        proc.wait()
        _ps_proc = None
        return {"success": True, "dit": original[:120], "voice": "fallback-TTS"}
    except Exception as e:
        return {"error": str(e)}


def play_mp3_blocking(path: str) -> subprocess.Popen:
    """Lance la lecture MP3 et retourne le processus avant sa fin."""
    uri = "file:///" + os.path.abspath(path).replace("\\", "/")
    ps = (
        "Add-Type -AssemblyName PresentationCore; "
        "$mp = New-Object System.Windows.Media.MediaPlayer; "
        f"$mp.Open([System.Uri]::new('{uri}')); "
        "while (-not $mp.NaturalDuration.HasTimeSpan) { Start-Sleep -Milliseconds 50 }; "
        "$ms = [int]$mp.NaturalDuration.TimeSpan.TotalMilliseconds + 50; "
        "$mp.Play(); "
        "Start-Sleep -Milliseconds $ms; "
        "$mp.Close()"
    )
    return subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_voice() -> dict:
    """Coupe la synthèse vocale en cours."""
    global _ps_proc
    _stopped.set()
    try:
        if _ps_proc and _ps_proc.poll() is None:
            _ps_proc.terminate()
        _ps_proc = None
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}
