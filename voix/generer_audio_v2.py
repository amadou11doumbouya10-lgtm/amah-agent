"""Script v2 — Approche démo, pas de prix, contact à la fin."""
import requests, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY  = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "cjVigY5qzO86Huf0OWal"
DIR      = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
HEADERS  = {"xi-api-key": API_KEY, "Content-Type": "application/json"}

SCRIPT = """
Vous avez déjà imaginé avoir un assistant qui travaille vraiment pour vous ? Pas un chatbot. Un vrai assistant. Amah Agent.

Regardez ce qui se passe quand vous lui dites : Organise mon bureau. En trois secondes, quarante-sept fichiers classés. Images, vidéos, documents — tout à sa place. Sans que vous n'ayez rien fait.

Dites-lui : Lis mes derniers emails. Elle les lit, les résume, et vous dit l'essentiel. Vous voulez répondre ? Elle rédige, vous validez.

Besoin d'un rapport Word sur votre réunion de ce matin ? Dites-le simplement. Le document est créé, formaté, prêt à être envoyé.

Amah peut aussi naviguer sur internet à votre place, chercher des informations, prendre des notes, traduire, donner la météo, générer des QR codes, ou simplement vous rappeler un rendez-vous dans une heure.

Ce qui rend Amah unique : tout se passe sur votre PC. Vos données ne quittent jamais votre machine. Pas de cloud. Pas d'abonnement. Pas de données partagées.

Soixante-cinq outils intégrés. Une interface simple. Une seule conversation.

Si Amah Agent vous intéresse pour votre activité, contactez-nous. Nous serons heureux de vous faire une démonstration personnalisée.

contact.amah.officiel@gmail.com. Amah Agent. L'IA qui agit vraiment.
""".strip()

print("Génération audio v2...")
resp = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
    headers=HEADERS,
    json={
        "text": SCRIPT,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.52, "similarity_boost": 0.82, "style": 0.25, "use_speaker_boost": True}
    }
)
if resp.status_code == 200:
    path = os.path.join(DIR, "amah_v2_audio.mp3")
    with open(path, "wb") as f: f.write(resp.content)
    print(f"Audio : {path}  ({os.path.getsize(path)//1024} Ko)")
    os.startfile(path)
else:
    print(f"Erreur {resp.status_code}: {resp.text}")
