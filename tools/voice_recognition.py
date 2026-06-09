import subprocess
import tempfile
import os


def listen(timeout: int = 7, language: str = "fr-FR") -> dict:
    """
    Écoute le microphone et retourne le texte reconnu.
    Utilise la reconnaissance vocale Google (internet requis) via SpeechRecognition.
    timeout : durée max d'écoute en secondes
    language : code langue (fr-FR, en-US, es-ES, ar-SA...)
    """
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 1.0          # tolère les pauses dans une phrase
        recognizer.dynamic_energy_threshold = True # s'adapte au bruit ambiant en temps réel
        recognizer.energy_threshold = 300

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1.0)   # calibration fiable
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)

        # Essai en fr-FR d'abord, fallback en-US si Google ne comprend rien
        for lang in (language, "en-US") if language != "en-US" else ("en-US",):
            try:
                text = recognizer.recognize_google(audio, language=lang)
                return {"success": True, "texte": text, "langue": lang}
            except sr.UnknownValueError:
                continue

        return {"error": "Je n'ai pas compris. Parle plus lentement ou approche-toi du micro."}

    except ImportError:
        return {"error": "SpeechRecognition manquant — lance : pip install SpeechRecognition pyaudio"}
    except Exception as e:
        if "no default input device" in str(e).lower():
            return {"error": "Aucun microphone detecte. Verifie que ton micro est branche."}
        if "timeout" in str(e).lower():
            return {"error": f"Temps d'ecoute depasse ({timeout}s). Aucune voix detectee."}
        return {"error": str(e)}


def listen_continuous(duration: int = 10, language: str = "fr-FR") -> dict:
    """
    Écoute pendant X secondes et retourne tout ce qui a été dit.
    """
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 1.2

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1.0)
            audio = recognizer.listen(source, timeout=duration, phrase_time_limit=duration)

        for lang in (language, "en-US") if language != "en-US" else ("en-US",):
            try:
                text = recognizer.recognize_google(audio, language=lang)
                return {"success": True, "texte": text, "duree": duration, "langue": lang}
            except sr.UnknownValueError:
                continue

        return {"error": "Aucun mot reconnu. Parle plus fort ou approche-toi du micro."}

    except Exception as e:
        return {"error": str(e)}
