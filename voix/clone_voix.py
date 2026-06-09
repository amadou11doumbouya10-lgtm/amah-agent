"""Clone la voix et génère le script audio via l'API ElevenLabs."""
import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY    = os.getenv("ELEVENLABS_API_KEY")
AUDIO_FILE = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix\Enregistrement.m4a"
HEADERS    = {"xi-api-key": API_KEY}

# ── 1. Cloner la voix ────────────────────────────────────────────────────────
print("Clonage de la voix en cours...")

with open(AUDIO_FILE, "rb") as f:
    resp = requests.post(
        "https://api.elevenlabs.io/v1/voices/add",
        headers=HEADERS,
        data={"name": "Voix Amah Agent", "description": "Voix presentateur Amah"},
        files={"files": ("Enregistrement.m4a", f, "audio/mp4")},
    )

if resp.status_code == 200:
    voice_id = resp.json()["voice_id"]
    print(f"Voix clonee ! Voice ID : {voice_id}")

    # Sauvegarde le voice_id pour usage ulterieur
    with open(r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix\voice_id.txt", "w") as vf:
        vf.write(voice_id)
    print("Voice ID sauvegarde dans voix/voice_id.txt")
else:
    print(f"Erreur {resp.status_code} : {resp.text}")
