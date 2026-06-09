"""
Vidéo présentation Amah Agent — Design premium 2024
Style : Dark glassmorphism · Gold glow · Bento grid · Oversized typography
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess, os, math, random

FFMPEG  = r"C:\Users\Smarte technologui\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
DIR     = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
AUDIO   = os.path.join(DIR, "amah_presentation.mp3")
VIDEO   = os.path.join(DIR, "amah_v2.mp4")
W, H    = 1920, 1080

# Palette premium
BG      = (8,   7,   5)
BG2     = (16,  14,  9)
GOLD    = (212, 180, 110)
GOLD_B  = (255, 220, 140)
GOLD_D  = (100, 78,  35)
WHITE   = (240, 235, 220)
GREY    = (130, 125, 110)
DIM     = (50,  48,  40)
RED     = (180, 60,  60)
GREEN   = (80,  180, 100)


def font(size, bold=True):
    names = ["arialbd.ttf","calibrib.ttf","segoeuib.ttf"] if bold else ["arial.ttf","calibri.ttf","segoeui.ttf"]
    for n in names:
        try: return ImageFont.truetype(f"C:/Windows/Fonts/{n}", size)
        except: pass
    return ImageFont.load_default(size=size)


def glow(base, color, radius=40, alpha=120):
    """Crée un effet de lueur autour d'une zone."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([W//2-300, H//2-200, W//2+300, H//2+200], fill=(*color, alpha))
    return layer.filter(ImageFilter.GaussianBlur(radius))


def gradient_bg(w=W, h=H, c1=BG, c2=BG2, radial=True):
    """Fond avec dégradé radial ou linéaire."""
    img = Image.new("RGB", (w, h), c1)
    draw = ImageDraw.Draw(img)
    if radial:
        cx, cy = w // 2, h // 2
        for r in range(max(w, h), 0, -4):
            t = r / max(w, h)
            color = tuple(int(c1[i] * (1-t) + c2[i] * t) for i in range(3))
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color)
    return img


def grid_pattern(img, spacing=80, alpha=15):
    """Grille subtile en arrière-plan."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for x in range(0, W, spacing):
        d.line([(x, 0), (x, H)], fill=(*GOLD_D, alpha), width=1)
    for y in range(0, H, spacing):
        d.line([(0, y), (W, y)], fill=(*GOLD_D, alpha), width=1)
    base = img.convert("RGBA")
    return Image.alpha_composite(base, overlay).convert("RGB")


def draw_glow_text(draw, text, x, y, f, color, glow_color=None, glow_r=20):
    """Texte avec effet de lueur."""
    gc = glow_color or color
    for dx in range(-glow_r, glow_r+1, 4):
        for dy in range(-glow_r, glow_r+1, 4):
            if dx*dx + dy*dy <= glow_r*glow_r:
                a = max(0, 30 - int(30 * math.sqrt(dx*dx+dy*dy) / glow_r))
                draw.text((x+dx, y+dy), text, font=f, fill=(*gc, a))
    draw.text((x, y), text, font=f, fill=color)


def center_text(draw, text, y, f, color=WHITE, img_w=W):
    bb = draw.textbbox((0, 0), text, font=f)
    x = (img_w - (bb[2]-bb[0])) / 2 - bb[0]
    return x, y


def card(draw, x, y, w, h, border_color=GOLD_D, fill=(20, 18, 12), radius=20, glow_a=60):
    """Carte glassmorphism avec bordure dorée."""
    # Fond de la carte
    draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=fill)
    # Bordure
    draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, outline=border_color, width=2)
    # Ligne lumineuse en haut
    draw.rounded_rectangle([x+2, y+2, x+w-2, y+12], radius=radius, fill=(*GOLD, glow_a))


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — TITRE (style Apple Keynote)
# ══════════════════════════════════════════════════════════════════════════════
def slide_titre():
    img = gradient_bg(c1=(10,8,4), c2=(25,20,8))
    img = grid_pattern(img, spacing=100, alpha=12)

    # Halo central doré
    halo = Image.new("RGBA", (W, H), (0,0,0,0))
    hd   = ImageDraw.Draw(halo)
    for r, a in [(600,20),(400,35),(250,50),(150,30)]:
        hd.ellipse([W//2-r, H//2-r, W//2+r, H//2+r], fill=(*GOLD_D, a))
    halo = halo.filter(ImageFilter.GaussianBlur(80))
    img  = Image.alpha_composite(img.convert("RGBA"), halo).convert("RGB")

    draw = ImageDraw.Draw(img)

    # Badge "NEW"
    draw.rounded_rectangle([W//2-60, 100, W//2+60, 140], radius=20, fill=(*GOLD_D, 180))
    draw.text((W//2-38, 108), "v 1.0.0", font=font(24, False), fill=GOLD_B)

    # Titre géant
    fa = font(200)
    tx, ty = center_text(draw, "AMAH", 160, fa)
    draw_glow_text(draw, "AMAH", tx, ty, fa, GOLD_B, GOLD, 15)

    # Sous-titre
    fb = font(52, False)
    tx2, ty2 = center_text(draw, "Agent IA Local pour Windows", 410, fb)
    draw.text((tx2, ty2), "Agent IA Local pour Windows", font=fb, fill=WHITE)

    # Séparateur doré
    draw.rectangle([W//2-400, 500, W//2+400, 502], fill=(*GOLD, 150))

    # Tagline
    fc = font(34, False)
    tx3, _ = center_text(draw, "65 outils · Données locales · Voix · Email · Navigation", 530, fc)
    draw.text((tx3, 530), "65 outils · Données locales · Voix · Email · Navigation", font=fc, fill=GREY)

    # Icônes bas
    icons = ["📁", "📧", "🌐", "🗣️", "📊", "🧠", "🔐", "🌤️"]
    ix = W//2 - (len(icons)*90)//2
    for ic in icons:
        draw.text((ix, 800), ic, font=font(60, False), fill=(*GOLD, 180))
        ix += 90

    return img


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — PROBLÈME (cartes avec icônes)
# ══════════════════════════════════════════════════════════════════════════════
def slide_probleme():
    img  = gradient_bg(c1=(10,5,5), c2=(20,10,8))
    img  = grid_pattern(img, alpha=10)
    draw = ImageDraw.Draw(img)

    # Étiquette
    draw.rounded_rectangle([80, 50, 280, 90], radius=15, fill=(*RED, 40))
    draw.text((100, 55), "01 / LE PROBLÈME", font=font(26), fill=(*RED, 220))

    # Titre
    ft = font(90)
    tx, _ = center_text(draw, "L'IA qui répond", 130, ft)
    draw.text((tx, 130), "L'IA qui répond", font=ft, fill=WHITE)
    tx2, _ = center_text(draw, "n'agit pas.", 235, ft)
    draw_glow_text(draw, "n'agit pas.", tx2, 235, ft, GOLD_B, GOLD, 8)

    # 3 cartes problème
    problems = [
        ("❌", "Organiser vos fichiers", "ChatGPT lit, mais ne classe pas"),
        ("❌", "Envoyer vos emails", "Il suggère, il n'envoie pas"),
        ("❌", "Agir sur votre PC", "Pas d'accès à votre machine"),
    ]
    cx = 120
    for icon, title, sub in problems:
        card(draw, cx, 380, 550, 260, border_color=(*RED, 80), fill=(25,12,12))
        draw.text((cx+30, 410), icon, font=font(60), fill=(200,80,80))
        draw.text((cx+30, 490), title, font=font(42), fill=WHITE)
        draw.text((cx+30, 555), sub, font=font(28, False), fill=GREY)
        cx += 590

    return img


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — SOLUTION (terminal style + highlights)
# ══════════════════════════════════════════════════════════════════════════════
def slide_solution():
    img  = gradient_bg(c1=(5,10,5), c2=(8,18,8))
    img  = grid_pattern(img, alpha=8)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([80, 50, 300, 90], radius=15, fill=(*GREEN, 40))
    draw.text((100, 55), "02 / LA SOLUTION", font=font(26), fill=(*GREEN, 220))

    ft = font(80)
    draw.text((80, 130), "Amah agit.", font=ft, fill=WHITE)
    draw_glow_text(draw, "Vraiment.", 80, 235, ft, GOLD_B, GOLD, 10)

    # Terminal style cards
    demos = [
        ('"Organise mon bureau"',  '→ Tous vos fichiers classés en 3 secondes'),
        ('"Lis mes 5 derniers emails"', '→ Résumé complet, réponse prête'),
        ('"Crée un rapport Word"', '→ Document généré automatiquement'),
        ('"Rappelle-moi dans 1h"', '→ Notification Windows programmée'),
    ]
    y = 370
    for cmd, result in demos:
        # Fond terminal
        card(draw, 80, y, 1760, 130, border_color=(*GOLD_D, 120), fill=(15,20,10))
        draw.text((120, y+20), cmd, font=font(38), fill=GOLD_B)
        draw.text((120, y+75), result, font=font(32, False), fill=(*GREEN, 220))
        # Curseur
        draw.rectangle([100, y+15, 108, y+50], fill=(*GOLD, 180))
        y += 155

    return img


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — 65 OUTILS (Bento Grid)
# ══════════════════════════════════════════════════════════════════════════════
def slide_outils():
    img  = gradient_bg(c1=(8,7,4), c2=(18,15,6))
    img  = grid_pattern(img, spacing=120, alpha=15)
    draw = ImageDraw.Draw(img)

    ft = font(100)
    tx, _ = center_text(draw, "65 OUTILS", 30, ft)
    draw_glow_text(draw, "65", tx, 30, ft, GOLD_B, GOLD, 10)
    draw.text((tx + draw.textlength("65", font=ft) + 20, 30), "OUTILS", font=ft, fill=WHITE)

    sub = font(36, False)
    tsx, _ = center_text(draw, "Tout ce dont vous avez besoin, intégré.", 150, sub)
    draw.text((tsx, 150), "Tout ce dont vous avez besoin, intégré.", font=sub, fill=GREY)

    # Bento Grid — 3 colonnes
    bento = [
        # col1
        [("📁 Fichiers", "Organiser, chercher,\ndéplacer, classer", 0, 200, 580, 200),
         ("📧 Email Gmail", "Lire, envoyer,\nchercher", 0, 420, 580, 160),
         ("🌐 Internet", "Recherche DuckDuckGo\n+ lecture de pages", 0, 600, 580, 160)],
        # col2
        [("🧠 Mémoire", "Se souvient entre\nles sessions (SQLite)", 600, 200, 720, 370),
         ("📊 Excel", "Lire, créer,\nmodifier les tableurs", 600, 590, 720, 170)],
        # col3
        [("🗣️ Voix", "Parle et écoute", 1340, 200, 500, 150),
         ("🌤️ Météo", "Prévisions temps réel", 1340, 370, 500, 150),
         ("🔐 Licence", "Clé liée à votre PC", 1340, 540, 500, 220)],
    ]

    for col in bento:
        for (title, desc, x, y, w, h) in col:
            card(draw, x+60, y, w, h, border_color=(*GOLD_D, 150), fill=(18,16,8))
            draw.text((x+90, y+20), title, font=font(36), fill=GOLD)
            draw.text((x+90, y+75), desc, font=font(28, False), fill=GREY)

    return img


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — TECHNOLOGIE (stats et specs)
# ══════════════════════════════════════════════════════════════════════════════
def slide_tech():
    img  = gradient_bg(c1=(5,5,15), c2=(10,10,25))
    img  = grid_pattern(img, alpha=12)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([80, 50, 320, 90], radius=15, fill=(40,40,120,80))
    draw.text((100, 55), "04 / TECHNOLOGIE", font=font(26), fill=(160,160,255,220))

    ft = font(90)
    draw.text((80, 130), "Propulsée par", font=ft, fill=WHITE)
    draw_glow_text(draw, "Groq AI", 80, 235, ft, (180,160,255), (120,100,220), 12)

    specs = [
        ("⚡", "Llama 3.3-70B",    "Le modèle le plus puissant de Groq"),
        ("🔒", "100% Local",       "Données sur votre PC, jamais dans le cloud"),
        ("🧠", "Mémoire SQLite",   "Reprend la conversation où vous l'avez laissée"),
        ("🚀", "Standalone .exe",  "Aucune installation Python requise — 114 Mo"),
    ]
    y = 400
    for icon, title, desc in specs:
        card(draw, 80, y, 1760, 120, border_color=(80,80,180,120), fill=(12,12,28))
        draw.text((120, y+28), icon, font=font(44), fill=WHITE)
        draw.text((200, y+20), title, font=font(44), fill=(200,190,255))
        draw.text((200, y+75), desc, font=font(30, False), fill=GREY)
        y += 138

    return img


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — PRIX (pricing card premium)
# ══════════════════════════════════════════════════════════════════════════════
def slide_prix():
    img  = gradient_bg(c1=(8,7,4), c2=(20,16,6))
    img  = grid_pattern(img, alpha=10)

    # Halo doré central
    halo = Image.new("RGBA", (W, H), (0,0,0,0))
    hd   = ImageDraw.Draw(halo)
    hd.ellipse([W//2-500, 100, W//2+500, H-50], fill=(*GOLD_D, 30))
    halo = halo.filter(ImageFilter.GaussianBlur(120))
    img  = Image.alpha_composite(img.convert("RGBA"), halo).convert("RGB")

    draw = ImageDraw.Draw(img)

    # Grande carte centrale
    card(draw, 360, 60, 1200, 960, border_color=GOLD, fill=(14,12,6), radius=30, glow_a=80)

    # Étiquette
    draw.rounded_rectangle([760, 100, 1160, 150], radius=25, fill=(*GOLD, 40))
    tx, _ = center_text(draw, "LICENCE UNIQUE", 108, font(30), img_w=W)
    draw.text((tx, 108), "LICENCE UNIQUE", font=font(30), fill=GOLD_B)

    # Prix géant
    fp = font(200)
    tx, _ = center_text(draw, "199€", 180, fp)
    draw_glow_text(draw, "199€", tx, 180, fp, GOLD_B, GOLD, 15)

    draw.text((tx + 380, 340), "HT", font=font(40, False), fill=GREY)

    sub = font(36, False)
    tsx, _ = center_text(draw, "Paiement unique · Aucun abonnement", 430, sub)
    draw.text((tsx, 430), "Paiement unique · Aucun abonnement", font=sub, fill=GREY)

    # Séparateur
    draw.rectangle([500, 510, 1420, 512], fill=(*GOLD_D, 100))

    # Features
    features = [
        "✓  65 outils intégrés à vie",
        "✓  Mises à jour automatiques incluses",
        "✓  Licence liée à votre PC — sécurisée",
        "✓  Support par email",
        "✓  Installation en 2 minutes",
    ]
    y = 545
    fg = font(38, False)
    for feat in features:
        tx, _ = center_text(draw, feat, y, fg)
        draw.text((tx, y), feat, font=fg, fill=(*GREEN, 220))
        y += 72

    return img


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — CONTACT (fin cinématique)
# ══════════════════════════════════════════════════════════════════════════════
def slide_contact():
    img  = gradient_bg(c1=(8,7,4), c2=(25,20,8))
    img  = grid_pattern(img, spacing=80, alpha=18)

    # Grand halo
    halo = Image.new("RGBA", (W, H), (0,0,0,0))
    hd   = ImageDraw.Draw(halo)
    for r, a in [(700,15),(500,25),(300,40),(180,35)]:
        hd.ellipse([W//2-r, H//2-r, W//2+r, H//2+r], fill=(*GOLD_D, a))
    halo = halo.filter(ImageFilter.GaussianBlur(100))
    img  = Image.alpha_composite(img.convert("RGBA"), halo).convert("RGB")

    draw = ImageDraw.Draw(img)

    # Grand A
    fa = font(400)
    tx, _ = center_text(draw, "A", 80, fa)
    draw_glow_text(draw, "A", tx, 80, fa, (*GOLD_D, 60), GOLD_D, 20)

    # Titre
    ft = font(100)
    tx, _ = center_text(draw, "AMAH AGENT", 530, ft)
    draw_glow_text(draw, "AMAH AGENT", tx, 530, ft, GOLD_B, GOLD, 8)

    # Tagline
    ts = font(44, False)
    tx, _ = center_text(draw, "L'IA qui agit vraiment.", 660, ts)
    draw.text((tx, 660), "L'IA qui agit vraiment.", font=ts, fill=WHITE)

    # Ligne
    draw.rectangle([W//2-300, 750, W//2+300, 752], fill=(*GOLD, 120))

    # Contact
    tc = font(38, False)
    tx, _ = center_text(draw, "contact.amah.officiel@gmail.com", 780, tc)
    draw.text((tx, 780), "contact.amah.officiel@gmail.com", font=tc, fill=GOLD)

    tg = font(28, False)
    tx, _ = center_text(draw, "github.com/amadou11doumbouya10-lgtm/amah-agent", 840, tg)
    draw.text((tx, 840), "github.com/amadou11doumbouya10-lgtm/amah-agent", font=tg, fill=GREY)

    return img


# ══════════════════════════════════════════════════════════════════════════════
# ASSEMBLAGE
# ══════════════════════════════════════════════════════════════════════════════

SLIDES_CONFIG = [
    (slide_titre,    18),
    (slide_probleme, 14),
    (slide_solution, 22),
    (slide_outils,   26),
    (slide_tech,     18),
    (slide_prix,     18),
    (slide_contact,  14),
]

print("Création des slides premium...")
slide_paths = []
for i, (fn, _) in enumerate(SLIDES_CONFIG):
    print(f"  Slide {i+1}/7 — {fn.__name__}...")
    img  = fn()
    path = os.path.join(DIR, f"slide_v2_{i:02d}.png")
    img.save(path, "PNG")
    slide_paths.append(path)

# Durée audio
result = subprocess.run([FFMPEG, "-i", AUDIO, "-f", "null", "-"], capture_output=True, text=True)
duration = 100.0
for line in result.stderr.split("\n"):
    if "Duration:" in line:
        t = line.split("Duration:")[1].split(",")[0].strip()
        h, m, s = t.split(":")
        duration = int(h)*3600 + int(m)*60 + float(s)
        break

print(f"\nDurée audio : {duration:.1f}s")
weights = [s[1] for s in SLIDES_CONFIG]
total_w = sum(weights)
durations = [duration * w / total_w for w in weights]

print("Rendu des segments vidéo...")
parts = []
for i, (path, dur) in enumerate(zip(slide_paths, durations)):
    part = os.path.join(DIR, f"part_v2_{i:02d}.mp4")
    subprocess.run([
        FFMPEG, "-y", "-loop", "1", "-i", path,
        "-t", str(dur),
        "-vf", f"scale={W}:{H},fade=in:0:15,fade=out:st={max(0,dur-0.6):.2f}:d=0.6",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25",
        "-preset", "fast", part
    ], capture_output=True)
    print(f"  Segment {i+1} : {dur:.1f}s")
    parts.append(part)

# Concat
concat = os.path.join(DIR, "concat_v2.txt")
with open(concat, "w") as f:
    for p in parts: f.write(f"file '{p}'\n")

tmp = os.path.join(DIR, "slides_v2.mp4")
subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat, "-c", "copy", tmp], capture_output=True)

# Fusion audio + vidéo
print("\nAssemblage final...")
subprocess.run([
    FFMPEG, "-y", "-i", tmp, "-i", AUDIO,
    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", VIDEO
], capture_output=True)

size = os.path.getsize(VIDEO) / (1024*1024)
print(f"\nVIDÉO FINALE : {VIDEO}")
print(f"Taille : {size:.1f} Mo")
os.startfile(VIDEO)
