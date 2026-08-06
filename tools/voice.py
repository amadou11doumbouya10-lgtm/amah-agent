import asyncio
import os
import subprocess
import tempfile

import edge_tts

VOICE = "fr-FR-HenriNeural"

_ps_proc = None  # processus PowerShell de lecture en cours (pour stop_voice)


def speak(text: str, speed: int = 2) -> dict:
    """Synthese vocale via edge-tts (HenriNeural) avec fallback Windows TTS."""
    global _ps_proc
    safe = text.replace('"', ' ').replace("'", ' ').replace('\n', ' ')
    rate = f"+{max(-50, min(50, speed * 5))}%"

    # Tentative edge-tts (2 essais)
    for attempt in range(2):
        try:
            async def _gen():
                tts = edge_tts.Communicate(safe, voice=VOICE, rate=rate)
                path = tempfile.mktemp(suffix=".mp3")
                await tts.save(path)
                return path

            loop = asyncio.new_event_loop()
            try:
                path = loop.run_until_complete(asyncio.wait_for(_gen(), timeout=10))
            finally:
                loop.close()

            _ps_proc = play_mp3_blocking(path)
            _ps_proc = None
            try:
                os.unlink(path)
            except Exception:
                pass
            return {"success": True, "dit": text[:120], "voice": "Henri"}
        except Exception:
            if attempt == 0:
                continue  # 2e tentative

    # Fallback Windows TTS (toujours disponible, hors ligne)
    try:
        rate_wpm = max(100, min(300, 180 + speed * 10))
        ps = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {speed}; "
            f"$s.Speak(\"{safe}\");"
        )
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        proc.wait()
        return {"success": True, "dit": text[:120], "voice": "fallback-TTS"}
    except Exception as e:
        return {"error": str(e)}


def play_mp3_blocking(path: str) -> subprocess.Popen:
    """Joue un fichier MP3 en mode bloquant via Windows MediaPlayer COM."""
    uri = "file:///" + os.path.abspath(path).replace("\\", "/")
    ps = (
        "Add-Type -AssemblyName PresentationCore; "
        "$mp = New-Object System.Windows.Media.MediaPlayer; "
        f"$mp.Open([System.Uri]::new('{uri}')); "
        "while (-not $mp.NaturalDuration.HasTimeSpan) { Start-Sleep -Milliseconds 50 }; "
        "$ms = [int]$mp.NaturalDuration.TimeSpan.TotalMilliseconds + 500; "
        "$mp.Play(); "
        "Start-Sleep -Milliseconds $ms; "
        "$mp.Close()"
    )
    proc = subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    proc.wait()
    return proc


def stop_voice() -> dict:
    """Coupe la synthese vocale en cours."""
    global _ps_proc
    try:
        if _ps_proc and _ps_proc.poll() is None:
            _ps_proc.terminate()
        _ps_proc = None
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}
