import subprocess


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
        # Bloquant : on attend la fin réelle de la synthèse pour pouvoir
        # garantir au lieu d'estimer (les appelants tournent déjà en thread).
        result = subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
            creationflags=subprocess.CREATE_NO_WINDOW,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip()[:300] or "Echec de la synthese vocale"}
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
