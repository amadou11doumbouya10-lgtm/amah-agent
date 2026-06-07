import subprocess
import tempfile
import os


def listen(timeout: int = 5, language: str = "fr-FR") -> dict:
    """
    Écoute le microphone et retourne le texte reconnu.
    Utilise la reconnaissance vocale Google (internet requis) via SpeechRecognition.
    timeout : durée max d'écoute en secondes
    language : code langue (fr-FR, en-US, es-ES, ar-SA...)
    """
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 0.7
        recognizer.energy_threshold = 300

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=8)

        text = recognizer.recognize_google(audio, language=language)
        return {"success": True, "texte": text, "langue": language}

    except ImportError:
        return {"error": "SpeechRecognition manquant — lance : pip install SpeechRecognition pyaudio"}
    except Exception as e:
        if "no default input device" in str(e).lower():
            return {"error": "Aucun microphone detecte. Verifie que ton micro est branche."}
        if "could not understand" in str(e).lower() or "recognition" in str(e).lower():
            return {"error": "Je n'ai pas compris. Parle plus clairement ou approche-toi du micro."}
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
        results    = []

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=duration, phrase_time_limit=duration)

        text = recognizer.recognize_google(audio, language=language)
        return {"success": True, "texte": text, "duree": duration}

    except Exception as e:
        return {"error": str(e)}
