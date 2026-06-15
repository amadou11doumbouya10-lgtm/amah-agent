"""Génère un mockup visuel de l'interface Amah Agent améliorée."""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 960, 700

BG_DARK  = (26, 26, 23)
BG_PANEL = (34, 34, 32)
BG_INPUT = (37, 37, 34)
BG_MSG_A = (30, 28, 22)   # fond message Amah
BG_MSG_U = (22, 22, 20)   # fond message User
GOLD     = (200, 169, 110)
GOLD_DIM = (122, 95,  56)
GOLD_LT  = (230, 205, 155)
WHITE    = (232, 224, 208)
GREY     = (136, 136, 122)
DIM      = (74,  74,  66)
CYAN     = (0,   180, 200)
GREEN    = (80,  200, 100)
RED_C    = (200, 80,  80)
TOOL_C   = (154, 122, 69)
SEP      = (42,  42,  38)


def font(size, bold=True):
    for n in (["consola.ttf","consolab.ttf"] if not bold else ["consolab.ttf","consola.ttf"]):
        try: return ImageFont.truetype(f"C:/Windows/Fonts/{n}", size)
        except: pass
    for n in (["arialbd.ttf"] if bold else ["arial.ttf"]):
        try: return ImageFont.truetype(f"C:/Windows/Fonts/{n}", size)
        except: pass
    return ImageFont.load_default(size=size)


img  = Image.new("RGB", (W, H), BG_DARK)
draw = ImageDraw.Draw(img)

# ── Barre titre Windows ──────────────────────────────────────────────────────
draw.rectangle([0, 0, W, 28], fill=(20, 20, 18))
draw.text((10, 6), "The Amah — Agent Local  v1.3.0", font=font(11, False), fill=GREY)
# Boutons Windows
for cx, col in [(W-50, (200,60,60)), (W-90, (180,140,50)), (W-130, (60,160,60))]:
    draw.ellipse([cx-7, 9, cx+7, 23], fill=col)

# ── Header amélioré ──────────────────────────────────────────────────────────
draw.rectangle([0, 28, W, 95], fill=BG_PANEL)

# Logo miniature hexagone (cercle gold)
draw.ellipse([12, 36, 52, 76], fill=BG_DARK, outline=GOLD, width=2)
draw.text((22, 45), "A", font=font(22), fill=GOLD)

# Titre centré
draw.text((180, 34), "THE AMAH — AGENT LOCAL", font=font(16), fill=GOLD)
draw.text((218, 58), "v1.3.0  ·  65 outils  ·  Windows 11", font=font(10, False), fill=GREY)

# Boutons header droite — NOUVEAU : Effacer + Copier + Réinitialiser
for label, bx, col in [("Effacer", W-290, DIM), ("Copier", W-200, DIM), ("Reinit.", W-115, (80,50,30))]:
    bw = 74
    draw.rounded_rectangle([bx, 42, bx+bw, 68], radius=6, fill=col)
    draw.text((bx+8, 49), label, font=font(11, False), fill=GREY)

# Séparateur gold
draw.rectangle([0, 95, W, 97], fill=GOLD_DIM)

# ── Zone chat ────────────────────────────────────────────────────────────────

# Message 1 — User
y = 110
draw.rectangle([0, y, W, y+58], fill=BG_MSG_U)
draw.text((16, y+6), "[10:32]", font=font(9, False), fill=DIM)
draw.text((72, y+6), "Toi  >", font=font(11, False), fill=GREY)
draw.text((126, y+6), "organise mon bureau automatiquement", font=font(11, False), fill=WHITE)
draw.rectangle([0, y+55, W, y+58], fill=SEP)
y += 62

# Message 2 — Amah (outil utilisé)
draw.rectangle([0, y, W, y+82], fill=BG_MSG_A)
draw.text((16, y+6), "[10:31]", font=font(9, False), fill=DIM)
draw.text((72, y+6), "Amah >", font=font(11), fill=GOLD)
draw.text((142, y+6), "Dossier organisé avec succès.", font=font(11, False), fill=WHITE)
draw.text((142, y+28), "47 fichiers déplacés — Images/ Vidéos/ Documents/ Archives/", font=font(10, False), fill=WHITE)
# Badge outil
draw.rounded_rectangle([142, y+50, 310, y+70], radius=8, fill=(40,30,15))
draw.text((152, y+54), "outil : organisation dossier", font=font(10, False), fill=TOOL_C)
draw.rectangle([0, y+79, W, y+82], fill=SEP)
y += 86

# Message 3 — User
draw.rectangle([0, y, W, y+58], fill=BG_MSG_U)
draw.text((16, y+6), "[10:33]", font=font(9, False), fill=DIM)
draw.text((72, y+6), "Toi  >", font=font(11, False), fill=GREY)
draw.text((126, y+6), "lis mes emails", font=font(11, False), fill=WHITE)
draw.rectangle([0, y+55, W, y+58], fill=SEP)
y += 62

# Message 4 — Amah (modèle indiqué) — NOUVEAU
draw.rectangle([0, y, W, y+100], fill=BG_MSG_A)
draw.text((16, y+6), "[10:33]", font=font(9, False), fill=DIM)
draw.text((72, y+6), "Amah >", font=font(11), fill=GOLD)
# NOUVEAU : badge modèle
draw.rounded_rectangle([142, y+6, 192, y+24], radius=6, fill=(20,40,20))
draw.text((150, y+9), "70B", font=font(10), fill=GREEN)
draw.text((72, y+30), "3 derniers emails :", font=font(10, False), fill=GREY)
draw.text((72, y+48), "1. Google — Alerte de sécurité — Hier", font=font(10, False), fill=WHITE)
draw.text((72, y+64), "2. LinkedIn — 10 nouvelles connexions", font=font(10, False), fill=WHITE)
# Badge outil
draw.rounded_rectangle([72, y+76, 320, y+94], radius=8, fill=(40,30,15))
draw.rectangle([0, y+97, W, y+100], fill=SEP)
y += 104

# Message 5 — User (simple) → 8B
draw.rectangle([0, y, W, y+58], fill=BG_MSG_U)
draw.text((16, y+6), "[10:35]", font=font(9, False), fill=DIM)
draw.text((72, y+6), "Toi  >", font=font(11, False), fill=GREY)
draw.text((126, y+6), "merci", font=font(11, False), fill=WHITE)
draw.rectangle([0, y+55, W, y+58], fill=SEP)
y += 62

# Message 6 — Amah 8B — NOUVEAU badge modèle rapide
draw.rectangle([0, y, W, y+68], fill=BG_MSG_A)
draw.text((16, y+6), "[10:35]", font=font(9, False), fill=DIM)
draw.text((72, y+6), "Amah >", font=font(11), fill=GOLD)
# NOUVEAU : badge 8B (rapide)
draw.rounded_rectangle([142, y+6, 196, y+24], radius=6, fill=(20,20,50))
draw.text((150, y+9), "8B ⚡", font=font(10), fill=CYAN)
draw.text((72, y+30), "De rien ! N'hésitez pas si vous avez besoin d'autre chose.", font=font(11, False), fill=WHITE)
draw.rectangle([0, y+65, W, y+68], fill=SEP)
y += 72

# ── Barre de saisie améliorée ────────────────────────────────────────────────
draw.rectangle([0, H-106, W, H-36], fill=BG_INPUT)
draw.text((14, H-94), "Toi", font=font(10, False), fill=GREY)
draw.text((48, H-94), ">", font=font(13), fill=GOLD_DIM)
# Zone de saisie
draw.rounded_rectangle([70, H-100, W-120, H-42], radius=6, fill=(42,42,38))
draw.text((82, H-84), "Écris ton message ici... (Shift+Entrée = nouvelle ligne)", font=font(11, False), fill=DIM)
# Bouton envoyer
draw.rounded_rectangle([W-110, H-98, W-14, H-44], radius=8, fill=GOLD_DIM)
draw.text((W-92, H-82), "Envoyer", font=font(12), fill=BG_DARK)

# ── Barre d'état améliorée ───────────────────────────────────────────────────
draw.rectangle([0, H-36, W, H], fill=BG_PANEL)

# NOUVEAU : indicateurs
draw.text((14, H-24), "Pret", font=font(10, False), fill=GREEN)

# NOUVEAU : clé active
draw.rounded_rectangle([70, H-30, 130, H-10], radius=4, fill=(30,25,10))
draw.text((78, H-26), "Cle 1/3", font=font(9, False), fill=GOLD_DIM)

# NOUVEAU : modèle actif
draw.rounded_rectangle([138, H-30, 204, H-10], radius=4, fill=(20,20,40))
draw.text((146, H-26), "70B actif", font=font(9, False), fill=CYAN)

# NOUVEAU : compteur tokens session
draw.rounded_rectangle([212, H-30, 310, H-10], radius=4, fill=(30,20,20))
draw.text((220, H-26), "~1 240 tokens", font=font(9, False), fill=(180, 100, 100))

# NOUVEAU : nombre messages
draw.text((320, H-24), "6 messages", font=font(9, False), fill=GREY)

# Hint droite
draw.text((W-370, H-24), "Shift+Entree  |  Ctrl+R  |  Ctrl+L effacer", font=font(9, False), fill=(50,50,45))

# ── Annotations (flèches expliquant les nouveautés) ───────────────────────────
# On dessine des encadrés NOUVEAU en or
for text, x, y2, w2 in [
    ("NOUVEAU : Bouton Effacer",        W-295, 75,  220),
    ("NOUVEAU : Badge modèle (8B/70B)", 196,   160, 240),
    ("NOUVEAU : Logo dans le header",   56,    75,  200),
    ("NOUVEAU : Clé active + tokens",   68,    H-8, 260),
]:
    draw.rectangle([x, y2-12, x+w2, y2+2], fill=(50,35,10))
    draw.text((x+4, y2-10), text, font=font(9, False), fill=GOLD)

# Sauvegarde
path = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\amah_ico_preview.png"
img.save(path)
print(f"Mockup: {path}")
import os; os.startfile(path)

