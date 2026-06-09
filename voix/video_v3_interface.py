"""
Vidéo v3 — Slides qui montrent l'interface Amah Agent
Style : Split-screen · Screenshot centré · Texte minimal
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess, os, math

FFMPEG = r"C:\Users\Smarte technologui\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
DIR    = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
SCR    = os.path.join(DIR, "screens")
AUDIO  = os.path.join(DIR, "amah_v2_audio.mp3")
VIDEO  = os.path.join(DIR, "amah_v3_interface.mp4")
W, H   = 1920, 1080

BG     = (8, 7, 5)
GOLD   = (212, 180, 110)
GOLD_B = (255, 220, 140)
GOLD_D = (90,  68,  28)
WHITE  = (240, 235, 220)
GREY   = (130, 125, 110)
DIM    = (40,  38,  30)


def font(size, bold=True):
    for n in (["arialbd.ttf","calibrib.ttf"] if bold else ["arial.ttf","calibri.ttf"]):
        try: return ImageFont.truetype(f"C:/Windows/Fonts/{n}", size)
        except: pass
    return ImageFont.load_default(size=size)


def base_bg(glow_x=W//2, glow_y=H//2, glow_r=500, glow_c=GOLD_D, glow_a=30):
    img = Image.new("RGB", (W, H), BG)
    # Grille subtile
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    d  = ImageDraw.Draw(ov)
    for x in range(0, W, 100):
        d.line([(x,0),(x,H)], fill=(*GOLD_D, 10), width=1)
    for y in range(0, H, 100):
        d.line([(0,y),(W,y)], fill=(*GOLD_D, 10), width=1)
    # Halo
    halo = Image.new("RGBA", (W, H), (0,0,0,0))
    hd   = ImageDraw.Draw(halo)
    for r2, a2 in [(glow_r, glow_a), (glow_r//2, glow_a*2), (glow_r//4, glow_a*3)]:
        hd.ellipse([glow_x-r2, glow_y-r2, glow_x+r2, glow_y+r2], fill=(*glow_c, a2))
    halo = halo.filter(ImageFilter.GaussianBlur(80))
    base = img.convert("RGBA")
    base = Image.alpha_composite(base, ov)
    base = Image.alpha_composite(base, halo)
    return base.convert("RGB")


def window_frame(screenshot_img, shadow=True):
    """Ajoute un cadre de fenêtre macOS-style autour du screenshot."""
    sw, sh = screenshot_img.size
    PAD    = 30
    TH     = 44  # titlebar height
    fw, fh = sw + PAD*2, sh + PAD*2 + TH
    frame  = Image.new("RGBA", (fw, fh), (0,0,0,0))
    fd     = ImageDraw.Draw(frame)
    # Ombre portée
    if shadow:
        shadow_l = Image.new("RGBA", (fw+40, fh+40), (0,0,0,0))
        sd = ImageDraw.Draw(shadow_l)
        sd.rounded_rectangle([20, 24, fw+20, fh+24], radius=18, fill=(0,0,0,120))
        shadow_l = shadow_l.filter(ImageFilter.GaussianBlur(18))
        frame_big = Image.new("RGBA", (fw+40, fh+40), (0,0,0,0))
        frame_big.paste(shadow_l, (0,0), shadow_l)
        frame_big.paste(frame, (20, 20), frame)
        frame  = frame_big
        fd     = ImageDraw.Draw(frame)
        fw, fh = fw+40, fh+40
        PAD   += 20
        TH    += 20
    # Corps de la fenêtre
    fd.rounded_rectangle([PAD-20, PAD-20+24, PAD-20+sw+40, PAD-20+24+sh+TH+4], radius=14, fill=(22,20,14,255))
    # Titlebar
    fd.rounded_rectangle([PAD-20, PAD-20+24, PAD-20+sw+40, PAD-20+24+TH], radius=14, fill=(32,30,22,255))
    # Boutons
    for cx, col in [(PAD-4, (237,95,85,255)), (PAD+18, (242,188,50,255)), (PAD+40, (100,200,86,255))]:
        fd.ellipse([cx, PAD+30, cx+14, PAD+44], fill=col)
    # Screenshot
    frame.paste(screenshot_img, (PAD, PAD+24+TH-16+20))
    return frame


def slide_intro():
    """Slide titre cinématique."""
    img  = base_bg(glow_c=GOLD_D, glow_a=25)
    draw = ImageDraw.Draw(img)
    # Grand A
    fa = font(340)
    bb = draw.textbbox((0,0), "A", font=fa)
    ax = (W - (bb[2]-bb[0])) // 2
    # Glow
    glow = Image.new("RGBA", (W, H), (0,0,0,0))
    gd   = ImageDraw.Draw(glow)
    gd.text((ax, 80), "A", font=fa, fill=(*GOLD_D, 80))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    img  = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text((ax, 80), "A", font=fa, fill=(*GOLD_D, 100))
    # Titre
    ft  = font(110)
    tx  = (W - (draw.textbbox((0,0),"AMAH AGENT",font=ft)[2])) // 2
    draw.text((tx, 500), "AMAH AGENT", font=ft, fill=GOLD_B)
    # Tagline
    fs  = font(40, False)
    tag = "L'assistant IA qui agit vraiment sur votre PC"
    tsx = (W - draw.textbbox((0,0),tag,font=fs)[2]) // 2
    draw.text((tsx, 640), tag, font=fs, fill=WHITE)
    # Ligne
    draw.rectangle([W//2-350, 720, W//2+350, 722], fill=(*GOLD, 120))
    # Badge
    badge = "65 outils · Local · Privé · Windows 11"
    fb    = font(30, False)
    bx    = (W - draw.textbbox((0,0),badge,font=fb)[2]) // 2
    draw.text((bx, 744), badge, font=fb, fill=GREY)
    return img


def slide_screen(screen_file, titre_gauche, sous_titre, badge=None, cote="droite"):
    """Slide avec screenshot de l'interface à droite/gauche."""
    img  = base_bg(glow_x=W*3//4 if cote=="droite" else W//4)
    scr  = Image.open(screen_file).convert("RGBA")
    # Redimensionner le screenshot
    scr_w = 920
    scr_h = int(scr.height * scr_w / scr.width)
    scr   = scr.resize((scr_w, scr_h), Image.LANCZOS)
    # Cadre fenêtre
    framed = window_frame(scr, shadow=True)
    fw, fh = framed.size
    # Positionner
    if cote == "droite":
        fx = W - fw + 60
        fy = (H - fh) // 2 - 20
        text_x = 80
    else:
        fx = -60
        fy = (H - fh) // 2 - 20
        text_x = scr_w + 80
    base = img.convert("RGBA")
    if fy < 0: fy = 0
    base.paste(framed, (fx, fy), framed)
    img  = base.convert("RGB")
    draw = ImageDraw.Draw(img)
    # Texte gauche
    ft = font(72)
    # Multi-lignes
    lines = titre_gauche.split("\n")
    ty = H//2 - len(lines)*50 - 40
    for line in lines:
        if line.startswith("*"):
            draw.text((text_x, ty), line[1:], font=ft, fill=GOLD_B)
        else:
            draw.text((text_x, ty), line, font=ft, fill=WHITE)
        ty += 90
    # Sous-titre
    fs  = font(34, False)
    for s in sous_titre.split("\n"):
        draw.text((text_x, ty+10), s, font=fs, fill=GREY)
        ty += 46
    # Badge
    if badge:
        draw.rounded_rectangle([text_x-5, ty+20, text_x+len(badge)*18, ty+60], radius=12, fill=(*GOLD_D, 60))
        draw.text((text_x+8, ty+28), badge, font=font(26, False), fill=GOLD)
    return img


def slide_contact():
    """Slide final contact — impact maximal."""
    img  = base_bg(glow_r=700, glow_a=35, glow_c=GOLD_D)
    draw = ImageDraw.Draw(img)
    # Ligne dorée haut
    draw.rectangle([0, 6, W, 10], fill=GOLD)
    draw.rectangle([0, H-10, W, H-6], fill=GOLD)
    # Titre
    ft = font(130)
    t1 = "Intéressé ?"
    tx = (W - draw.textbbox((0,0),t1,font=ft)[2]) // 2
    draw.text((tx, 140), t1, font=ft, fill=GOLD_B)
    # Sous-titre
    fs = font(50, False)
    t2 = "Contactez-nous pour une démonstration personnalisée."
    tsx = (W - draw.textbbox((0,0),t2,font=fs)[2]) // 2
    draw.text((tsx, 310), t2, font=fs, fill=WHITE)
    # Séparateur
    draw.rectangle([W//2-400, 410, W//2+400, 413], fill=(*GOLD, 100))
    # Email
    fe = font(56)
    email = "contact.amah.officiel@gmail.com"
    ex = (W - draw.textbbox((0,0),email,font=fe)[2]) // 2
    draw.text((ex, 450), email, font=fe, fill=GOLD)
    # GitHub
    fg = font(34, False)
    gh = "github.com/amadou11doumbouya10-lgtm/amah-agent"
    gx = (W - draw.textbbox((0,0),gh,font=fg)[2]) // 2
    draw.text((gx, 545), gh, font=fg, fill=GREY)
    # Tagline finale
    draw.rectangle([W//2-300, 640, W//2+300, 642], fill=(*GOLD_D, 120))
    ff = font(44, False)
    tag = "AMAH AGENT  ·  L'IA qui agit vraiment"
    tx2 = (W - draw.textbbox((0,0),tag,font=ff)[2]) // 2
    draw.text((tx2, 670), tag, font=ff, fill=(*GOLD, 180))
    return img


# ── Génération ───────────────────────────────────────────────────────────────
SLIDES_CONFIG = [
    (lambda: slide_intro(), 12),
    (lambda: slide_screen(
        os.path.join(SCR,"screen1_accueil.png"),
        "Dites-lui ce\n*que vous voulez.",
        "Amah organise vos fichiers\nen 3 secondes.",
        badge="📁 Organisation automatique",
        cote="droite"), 18),
    (lambda: slide_screen(
        os.path.join(SCR,"screen2_email.png"),
        "Vos emails,\n*résumés.",
        "Lire, résumer, répondre.\nSans ouvrir votre boîte mail.",
        badge="📧 Email Gmail intégré",
        cote="gauche"), 18),
    (lambda: slide_screen(
        os.path.join(SCR,"screen3_document.png"),
        "Créez des\n*documents.",
        "Word, PDF, Excel, TXT.\nGénérés automatiquement.",
        badge="📄 65 types de documents",
        cote="droite"), 18),
    (lambda: slide_screen(
        os.path.join(SCR,"screen4_navigateur.png"),
        "Elle navigue\n*pour vous.",
        "LinkedIn, Google, n'importe quel site.\nElle lit et vous résume.",
        badge="🌐 Navigation Chrome visible",
        cote="gauche"), 16),
    (lambda: slide_contact(), 12),
]

print("Génération slides interface...")
slide_paths = []
for i, (fn, _) in enumerate(SLIDES_CONFIG):
    print(f"  Slide {i+1}/{len(SLIDES_CONFIG)}...")
    img  = fn()
    path = os.path.join(DIR, f"slide_v3_{i:02d}.png")
    img.save(path, "PNG")
    slide_paths.append(path)

# Durée audio
result = subprocess.run([FFMPEG, "-i", AUDIO, "-f", "null", "-"], capture_output=True, text=True)
duration = 90.0
for line in result.stderr.split("\n"):
    if "Duration:" in line:
        t = line.split("Duration:")[1].split(",")[0].strip()
        h, m, s = t.split(":")
        duration = int(h)*3600 + int(m)*60 + float(s)
        break
print(f"\nDurée : {duration:.1f}s")

weights   = [s[1] for s in SLIDES_CONFIG]
total_w   = sum(weights)
durations = [duration * w / total_w for w in weights]

print("Rendu segments...")
parts = []
for i, (path, dur) in enumerate(zip(slide_paths, durations)):
    part = os.path.join(DIR, f"part_v3_{i:02d}.mp4")
    subprocess.run([
        FFMPEG, "-y", "-loop", "1", "-i", path,
        "-t", str(dur),
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fade=in:0:12,fade=out:st={max(0,dur-0.5):.2f}:d=0.5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25", "-preset", "fast", part
    ], capture_output=True)
    print(f"  Segment {i+1} : {dur:.1f}s")
    parts.append(part)

concat = os.path.join(DIR, "concat_v3.txt")
with open(concat, "w") as f:
    for p in parts: f.write(f"file '{p}'\n")

tmp = os.path.join(DIR, "slides_v3.mp4")
subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat, "-c", "copy", tmp], capture_output=True)

print("\nAssemblage final...")
subprocess.run([
    FFMPEG, "-y", "-i", tmp, "-i", AUDIO,
    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", VIDEO
], capture_output=True)

size = os.path.getsize(VIDEO) / (1024*1024)
print(f"\nVIDÉO : {VIDEO}  ({size:.1f} Mo)")
os.startfile(VIDEO)
