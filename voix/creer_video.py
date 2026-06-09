"""Crée la vidéo de présentation Amah Agent — slides + audio."""
from PIL import Image, ImageDraw, ImageFont
import subprocess
import os
import json

FFMPEG   = r"C:\Users\Smarte technologui\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
OUT_DIR  = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
AUDIO    = os.path.join(OUT_DIR, "amah_presentation.mp3")
VIDEO    = os.path.join(OUT_DIR, "amah_presentation.mp4")

W, H     = 1920, 1080
BG       = (20, 18, 12)
GOLD     = (200, 169, 110)
GOLD_DIM = (122, 95, 56)
WHITE    = (232, 224, 208)
GREY     = (100, 98, 90)


def font(size, bold=True):
    for name in ["arialbd.ttf" if bold else "arial.ttf", "calibrib.ttf", "segoeuib.ttf"]:
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
        except:
            pass
    return ImageFont.load_default(size=size)


def new_slide():
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    # Bande dorée en haut
    draw.rectangle([0, 0, W, 6], fill=GOLD)
    # Bande dorée en bas
    draw.rectangle([0, H-6, W, H], fill=GOLD)
    return img, draw


def texte_centre(draw, text, y, f, color=WHITE, max_w=1600):
    bb   = draw.textbbox((0, 0), text, font=f)
    tw   = bb[2] - bb[0]
    x    = (W - min(tw, max_w)) / 2
    draw.text((x, y), text, font=f, fill=color)


def slide_titre():
    img, draw = new_slide()
    # Logo A
    fa = font(220)
    draw.text((W//2 - 80, 150), "A", font=fa, fill=GOLD)
    # Titre
    texte_centre(draw, "THE AMAH", 420, font(90), GOLD)
    texte_centre(draw, "AGENT IA LOCAL", 530, font(50), WHITE)
    # Ligne déco
    draw.rectangle([W//2 - 300, 620, W//2 + 300, 623], fill=GOLD_DIM)
    texte_centre(draw, "65 outils · Windows 11 · Votre données restent sur votre PC", 650, font(28, False), GREY)
    return img


def slide_section(titre, lignes, numero=""):
    img, draw = new_slide()
    if numero:
        draw.text((80, 60), numero, font=font(36, False), fill=GOLD_DIM)
    texte_centre(draw, titre, 160, font(72), GOLD)
    draw.rectangle([W//2 - 250, 270, W//2 + 250, 274], fill=GOLD_DIM)
    y = 330
    for ligne in lignes:
        if ligne.startswith("•"):
            draw.text((200, y), ligne, font=font(38, False), fill=WHITE)
        else:
            texte_centre(draw, ligne, y, font(38, False), WHITE)
        y += 75
    return img


def slide_outils():
    img, draw = new_slide()
    texte_centre(draw, "65 OUTILS INTÉGRÉS", 80, font(68), GOLD)
    draw.rectangle([W//2 - 250, 180, W//2 + 250, 184], fill=GOLD_DIM)

    cats = [
        ("📁 Fichiers & Documents",  "📧 Email Gmail"),
        ("🌐 Recherche Internet",    "🌍 Navigation Chrome"),
        ("🧠 Mémoire Persistante",   "📊 Excel & Archives"),
        ("🗣️ Voix & Notifications",  "🌤️ Météo & Traduction"),
        ("🔐 Licence Sécurisée",     "⚙️ Système Windows"),
    ]
    y = 230
    for g, d in cats:
        draw.text((160, y),       g, font=font(34, False), fill=WHITE)
        draw.text((W//2 + 60, y), d, font=font(34, False), fill=WHITE)
        draw.line([W//2, y, W//2, y+50], fill=GOLD_DIM, width=1)
        y += 70
    return img


def slide_prix():
    img, draw = new_slide()
    texte_centre(draw, "TARIFICATION", 120, font(68), GOLD)
    draw.rectangle([W//2 - 200, 220, W//2 + 200, 224], fill=GOLD_DIM)

    # Grand prix
    texte_centre(draw, "199 €", 310, font(160), GOLD)
    texte_centre(draw, "LICENCE UNIQUE — PAIEMENT UNE SEULE FOIS", 490, font(36), WHITE)

    # Avantages
    avantages = [
        "✓  Aucun abonnement mensuel",
        "✓  65 outils inclus à vie",
        "✓  Mises à jour automatiques",
        "✓  Support inclus",
    ]
    y = 600
    for av in avantages:
        texte_centre(draw, av, y, font(36, False), (160, 220, 160))
        y += 70
    return img


def slide_contact():
    img, draw = new_slide()
    texte_centre(draw, "AMAH AGENT", 200, font(90), GOLD)
    texte_centre(draw, "L'IA qui agit vraiment.", 320, font(52, False), WHITE)
    draw.rectangle([W//2 - 300, 420, W//2 + 300, 424], fill=GOLD_DIM)
    texte_centre(draw, "📧 contact.amah.officiel@gmail.com", 470, font(42), GOLD)
    texte_centre(draw, "github.com/amadou11doumbouya10-lgtm/amah-agent", 560, font(32, False), GREY)
    texte_centre(draw, "Licence unique · 199 € · Windows 11", 670, font(36, False), WHITE)
    return img


# ── Génère les slides ────────────────────────────────────────────────────────
SLIDES = [
    (slide_titre(),       18),
    (slide_section("LE PROBLÈME", [
        "• ChatGPT répond. Il n'agit pas.",
        "• Il ne peut pas organiser vos fichiers.",
        "• Il ne peut pas envoyer vos emails.",
        "• Il n'a pas accès à votre PC.",
    ], "01"), 14),
    (slide_section("LA SOLUTION", [
        '"Organise mon bureau"  →  fait en 3 secondes',
        '"Lis mes emails"  →  résumé immédiat',
        '"Crée un rapport Word"  →  généré automatiquement',
    ], "02"), 22),
    (slide_outils(),      28),
    (slide_section("TECHNOLOGIE", [
        "Intelligence Artificielle : Groq · Llama 3.3-70B",
        "Mémoire persistante entre les sessions",
        "100% local · Données sécurisées sur votre PC",
        "Windows 11 · Standalone · Aucune installation",
    ], "04"), 18),
    (slide_prix(),        18),
    (slide_contact(),     14),
]

print("Création des slides...")
slide_paths = []
for i, (img, _) in enumerate(SLIDES):
    p = os.path.join(OUT_DIR, f"slide_{i:02d}.png")
    img.save(p)
    slide_paths.append(p)
    print(f"  slide_{i:02d}.png")

# ── Durée audio ──────────────────────────────────────────────────────────────
result = subprocess.run(
    [FFMPEG, "-i", AUDIO, "-f", "null", "-"],
    capture_output=True, text=True
)
duration = 130.0  # fallback
for line in result.stderr.split("\n"):
    if "Duration:" in line:
        t = line.split("Duration:")[1].split(",")[0].strip()
        h, m, s = t.split(":")
        duration = int(h)*3600 + int(m)*60 + float(s)
        break
print(f"\nDurée audio : {duration:.1f}s")

# ── Calcul des durées par slide ──────────────────────────────────────────────
weights = [s[1] for s in SLIDES]
total_w = sum(weights)
durations = [duration * w / total_w for w in weights]

# ── Création d'une liste de segments pour concat ────────────────────────────
concat_file = os.path.join(OUT_DIR, "concat.txt")
video_parts  = []

print("\nCréation des segments vidéo...")
for i, (path, dur) in enumerate(zip(slide_paths, durations)):
    part = os.path.join(OUT_DIR, f"part_{i:02d}.mp4")
    subprocess.run([
        FFMPEG, "-y",
        "-loop", "1",
        "-i", path,
        "-t", str(dur),
        "-vf", "scale=1920:1080",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        part
    ], capture_output=True)
    video_parts.append(part)
    print(f"  Segment {i} : {dur:.1f}s")

# ── Concaténation des segments ───────────────────────────────────────────────
with open(concat_file, "w") as f:
    for p in video_parts:
        f.write(f"file '{p}'\n")

temp_video = os.path.join(OUT_DIR, "slides_only.mp4")
subprocess.run([
    FFMPEG, "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", concat_file,
    "-c", "copy",
    temp_video
], capture_output=True)

# ── Fusion vidéo + audio ─────────────────────────────────────────────────────
print("\nAssemblage final vidéo + audio...")
subprocess.run([
    FFMPEG, "-y",
    "-i", temp_video,
    "-i", AUDIO,
    "-c:v", "copy",
    "-c:a", "aac",
    "-shortest",
    VIDEO
], capture_output=True)

size = os.path.getsize(VIDEO) / (1024*1024)
print(f"\nVIDÉO FINALE : {VIDEO}")
print(f"Taille : {size:.1f} Mo")
os.startfile(VIDEO)
