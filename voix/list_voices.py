import requests
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.getenv("ELEVENLABS_API_KEY")
resp = requests.get(
    "https://api.elevenlabs.io/v1/voices",
    headers={"xi-api-key": API_KEY}
)

voices = resp.json().get("voices", [])

# Filtre voix françaises ou compatibles
print("=== VOIX DISPONIBLES ===\n")
for v in voices:
    labels = v.get("labels", {})
    lang   = labels.get("language", "").lower()
    acc    = labels.get("accent", "").lower()
    cat    = v.get("category", "")
    name   = v.get("name", "")
    vid    = v.get("voice_id", "")
    desc   = labels.get("description", "")

    if lang in ("french", "fr") or acc in ("french", "fr"):
        print(f"[FR] {name}")
        print(f"     ID      : {vid}")
        print(f"     Accent  : {acc} | Langue : {lang}")
        print(f"     Style   : {desc}")
        print(f"     Categorie: {cat}")
        print()

print("\n=== TOUTES LES VOIX (pour choisir manuellement) ===\n")
for v in voices:
    labels = v.get("labels", {})
    print(f"{v['name']:25} | {labels.get('language','?'):10} | {labels.get('accent','?'):15} | {v.get('category','')}")
