import subprocess
import threading


def speak(text: str, speed: int = 2) -> dict:
    """
    Synthèse vocale via Windows System.Speech (aucune dépendance externe).
    speed : -10 (très lent) à 10 (très rapide), défaut 2
    """
    try:
        safe = text.replace("'", " ").replace('"', " ").replace("\n", " ")
        ps   = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {speed}; "
            f"$s.Speak('{safe}')"
        )
        threading.Thread(
            target=lambda: subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                creationflags=subprocess.CREATE_NO_WINDOW
            ),
            daemon=True
        ).start()
        return {"success": True, "dit": text[:120]}
    except Exception as e:
        return {"error": str(e)}


def stop_voice() -> dict:
    """Coupe la synthèse vocale en cours."""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command",
             "Add-Type -AssemblyName System.Speech; "
             "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.SpeakAsyncCancelAll()"],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}
