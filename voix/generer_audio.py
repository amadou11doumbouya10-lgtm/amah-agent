"""Génère l'audio complet de la présentation Amah Agent avec la voix Eric."""
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY  = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "cjVigY5qzO86Huf0OWal"  # Eric
OUT_DIR  = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
HEADERS  = {"xi-api-key": API_KEY, "Content-Type": "application/json"}

SCRIPT = """
Imaginez un assistant intelligent installé directement sur votre PC Windows. Pas dans le cloud. Pas sur un serveur distant. Sur votre machine. C'est Amah Agent.

Les assistants IA comme ChatGPT répondent à vos questions. Mais ils ne peuvent pas organiser vos fichiers, envoyer vos emails, ni agir concrètement sur votre ordinateur. Amah, elle, peut tout faire.

Dites-lui : Organise mon bureau. Elle classe tous vos fichiers en quelques secondes. Dites-lui : Lis mes cinq derniers emails. Elle les lit et vous les résume. Dites-lui : Crée un rapport Word sur notre réunion. Le document est généré immédiatement.

Amah Agent dispose de soixante-cinq outils intégrés : gestion de fichiers, création de documents Word et PDF, recherche internet, email Gmail, navigation web automatique, Excel, traduction, météo, rappels, et bien plus encore. Le tout sans connexion internet permanente. Vos données restent sur votre PC.

Propulsée par l'intelligence artificielle Groq et le modèle Llama 3.3, Amah fonctionne en temps réel avec une vitesse remarquable. Elle se souvient de vos préférences entre chaque session grâce à une mémoire persistante.

Amah Agent est disponible en licence unique à cent quatre-vingt-dix-neuf euros, sans abonnement mensuel. Un seul paiement, une utilisation à vie sur votre PC.

Pour une démonstration ou pour obtenir votre licence, contactez-nous à contact.amah.officiel@gmail.com. Amah Agent. L'IA qui agit vraiment.
""".strip()

print("Generation de l'audio complet...")
resp = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
    headers=HEADERS,
    json={
        "text": SCRIPT,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability":        0.55,
            "similarity_boost": 0.80,
            "style":            0.20,
            "use_speaker_boost": True
        }
    }
)

if resp.status_code == 200:
    path = os.path.join(OUT_DIR, "amah_presentation.mp3")
    with open(path, "wb") as f:
        f.write(resp.content)
    size = os.path.getsize(path) / 1024
    print(f"Audio genere : {path}")
    print(f"Taille : {size:.0f} Ko")
    os.startfile(path)
else:
    print(f"Erreur {resp.status_code}: {resp.text}")
