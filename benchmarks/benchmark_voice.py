"""Compréhension vocale de bout en bout, sans micro : des phrases prononcées par
des voix de synthèse passent par le moteur de reconnaissance des interfaces
(Google, fr-FR), puis on vérifie ce qu'Amah comprend du texte obtenu.

Réseau requis (edge-tts + reconnaissance Google), AUCUN appel Groq, aucun son
joué. ffmpeg requis pour les voix edge-tts (sinon seule la voix Windows est testée).

Lancer depuis la racine du projet :
    py -3.13 -m benchmarks.benchmark_voice              # 4 voix, ~3 minutes
    py -3.13 -m benchmarks.benchmark_voice henri        # une voix

Ce que ce banc ne teste pas : la capture réelle du micro (seuils, bruit de ta
pièce), ta propre voix et ton accent, le mode Live Gemini.
Mesuré le 18/10/2026 : mot de réveil 6/8 (voix Windows trop robotique),
interface vocale 64/64, bouton micro et terminal 60/60.
Code de sortie 1 si une vérification échoue (hors voix Windows pour le réveil).
"""
import asyncio, glob, os, shutil, subprocess, sys, tempfile, wave

import speech_recognition as sr

import amah_listener
import voice_fullscreen as V
from config import TOOLS_DEFINITIONS
from tools.fastpath_v01 import _extract_calculation, normalize_text
from tools.instant import _BRIEFING, _STOP_READING, datetime_request_kind
from tools.memory_context import memory_context
from tools.tool_router import normalize, select_tools

PHRASES = [
    # (id, phrase dite, attendu)
    ("reveil", "Amah", "reveil"),
    ("reveil_question", "Amah, quelle heure est-il ?", "reveil"),
    ("heure", "Quelle heure est-il ?", "instant:heure"),
    ("point", "Fais-moi le point", "instant:briefing"),
    ("meteo", "Quel temps fait-il à Conakry ?", "outil:get_weather_simple|get_weather"),
    ("actualite", "Quelle est la dernière version de Python ?", "outil:web_search"),
    ("calcul", "Combien font douze fois quinze ?", "instant:calcul"),
    ("rappel", "Rappelle-moi dans dix minutes d'appeler Mamadou", "outil:set_reminder"),
    ("volume", "Mets le volume à trente pour cent", "outil:set_volume"),
    ("musique", "Mets de la musique de Didi B sur YouTube", "outil:play_music|open_youtube"),
    ("email", "Envoie un email à Fatou pour lui dire que la réunion est reportée à lundi",
     "outil:send_email|draft_email"),
    ("lecture", "Lis-moi à voix haute l'article de Wikipédia sur Conakry", "outil:read_aloud"),
    ("arret_lecture", "Arrête la lecture", "instant:arret"),
    ("fermer_appli", "Ferme Chrome", "outil:kill_process"),
    ("deux_etapes", "Cherche la météo de Conakry puis enregistre-la dans un fichier sur le bureau",
     "outil:get_weather_simple|get_weather+write_file|create_txt"),
    ("traduction", "Traduis bonjour tout le monde en anglais", "outil:translate"),
    ("memoire", "Tu te souviens de ce qu'on a dit sur la météo ?", "memoire"),
    ("au_revoir", "Au revoir Amah", "quitte"),
]
EDGE_VOICES = {"henri": "fr-FR-HenriNeural", "denise": "fr-FR-DeniseNeural", "henri_bruit": "fr-FR-HenriNeural"}
OUT = os.path.join(tempfile.gettempdir(), "amah_benchmark_voice")
listener = object.__new__(amah_listener.ListenerWidget)


def find_ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return found
    pattern = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages",
                           "*FFmpeg*", "*", "bin", "ffmpeg.exe")
    matches = glob.glob(pattern)
    return matches[0] if matches else None


FFMPEG = find_ffmpeg()


def ff(*args):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", *args], check=True)


def synth(voice, pid, text):
    wav = os.path.join(OUT, f"{voice}_{pid}.wav")
    if voice == "hortense":
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("voice", next(v.id for v in engine.getProperty("voices") if "Hortense" in v.name))
        engine.save_to_file(text, wav)
        engine.runAndWait()
        return wav
    import edge_tts
    mp3 = wav + ".mp3"
    asyncio.run(edge_tts.Communicate(text, voice=EDGE_VOICES[voice]).save(mp3))
    if voice == "henri_bruit":       # bruit de pièce (rose, ~ -30 dB)
        ff("-i", mp3, "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.035:sample_rate=16000",
           "-filter_complex", "[0:a]aresample=16000[v];[v][1:a]amix=inputs=2:duration=first:normalize=0",
           "-ac", "1", "-ar", "16000", wav)
    else:
        ff("-i", mp3, "-ac", "1", "-ar", "16000", wav)
    return wav


def recognize(wav, max_seconds=None):
    r = sr.Recognizer()
    with sr.AudioFile(wav) as src:
        audio = r.record(src, duration=max_seconds)
    try:
        return r.recognize_google(audio, language="fr-FR")
    except sr.UnknownValueError:
        return ""


def understood(t, expect):
    if not t:
        return False
    if expect == "reveil":
        return listener._is_wake(t.lower())
    if expect == "quitte":
        return V._is_quit_request(t)
    if expect == "memoire":
        try:
            res, _ = memory_context(t, summarize_fn=lambda p: (_ for _ in ()).throw(RuntimeError()))
        except Exception:
            res = None
        return res is not None
    if expect.startswith("instant:"):
        return bool({
            "heure": lambda: datetime_request_kind(t),
            "briefing": lambda: _BRIEFING.match(normalize(t)),
            "calcul": lambda: _extract_calculation(normalize_text(t)),
            "arret": lambda: _STOP_READING.match(t.strip()),
        }[expect.split(":")[1]]())
    names = {x["function"]["name"] for x in select_tools(t, TOOLS_DEFINITIONS)[0]}
    return all(any(n in names for n in g.split("|")) for g in expect.split(":", 1)[1].split("+"))


def main():
    os.makedirs(OUT, exist_ok=True)
    voices = sys.argv[1:] or ["henri", "denise", "hortense", "henri_bruit"]
    if not FFMPEG:
        print("ffmpeg introuvable : seule la voix Windows (hortense) est testée")
        voices = [v for v in voices if v == "hortense"]
    scores = {"reveil": [], "voix": [], "micro": []}
    failures = []
    for voice in voices:
        print(f"… voix {voice}", flush=True)
        for pid, text, expect in PHRASES:
            wav = synth(voice, pid, text)
            with wave.open(wav) as w:
                seconds = w.getnframes() / w.getframerate()
            heard = recognize(wav)
            if expect == "reveil":        # amah_listener : écoute de 3 s
                heard_3s = recognize(wav, 3.0) if seconds > 3 else heard
                ok = understood(heard_3s, "reveil")
                scores["reveil"].append(ok)
                if not ok and voice != "hortense":
                    failures.append((voice, "réveil", text, heard_3s))
                continue
            # Interface vocale : écoute de 12 s, fermeture sur "au revoir"…
            heard_12s = recognize(wav, 12.0) if seconds > 12 else heard
            closes = expect != "quitte" and V._is_quit_request(heard_12s)
            ok = understood(heard_12s, expect) and not closes
            scores["voix"].append(ok)
            if not ok:
                failures.append((voice, "voix" + (" (se ferme)" if closes else ""), text, heard_12s))
            # Bouton micro de la fenêtre et terminal : écoute de 15 s
            if expect != "quitte":
                ok = understood(heard, expect)
                scores["micro"].append(ok)
                if not ok:
                    failures.append((voice, "micro", text, heard))
    print()
    labels = {"reveil": "Mot de réveil", "voix": "Interface vocale", "micro": "Bouton micro + terminal"}
    for key, res in scores.items():
        print(f"{labels[key]:24} {sum(res)}/{len(res)}")
    for voice, where, text, heard in failures:
        print(f"  ÉCHEC {voice} / {where} : « {text} » entendu « {heard} »")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
