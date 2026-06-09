"""
Vidéos v4 — avec le vrai logo hexagone Amah Agent
Remplace le A généré par le vrai SVG converti en PNG.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess, os

FFMPEG  = r"C:\Users\Smarte technologui\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
DIR     = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
LOGO    = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\amah_logo_hex.png"
SCR     = os.path.join(DIR, "screens")
W, H    = 1920, 1080
VW, VH  = 1080, 1920

BG      = (8, 7, 5)
GOLD    = (212, 180, 110)
GOLD_B  = (255, 220, 140)
GOLD_D  = (90, 68, 28)
WHITE   = (240, 235, 220)
GREY    = (130, 125, 110)
CYAN    = (0, 229, 255)

logo_img = Image.open(LOGO).convert("RGBA")


def font(size, bold=True):
    for n in (["arialbd.ttf","calibrib.ttf"] if bold else ["arial.ttf","calibri.ttf"]):
        try: return ImageFont.truetype(f"C:/Windows/Fonts/{n}", size)
        except: pass
    return ImageFont.load_default(size=size)


def base_bg(w=W, h=H, glow_c=GOLD_D, glow_a=25):
    img = Image.new("RGB", (w, h), BG)
    ov  = Image.new("RGBA", (w, h), (0,0,0,0))
    d   = ImageDraw.Draw(ov)
    for x in range(0, w, 100): d.line([(x,0),(x,h)], fill=(*GOLD_D, 8), width=1)
    for y in range(0, h, 100): d.line([(0,y),(w,y)], fill=(*GOLD_D, 8), width=1)
    halo = Image.new("RGBA", (w, h), (0,0,0,0))
    hd   = ImageDraw.Draw(halo)
    hd.ellipse([w//2-500, h//2-400, w//2+500, h//2+400], fill=(*glow_c, glow_a))
    halo = halo.filter(ImageFilter.GaussianBlur(100))
    base = img.convert("RGBA")
    base = Image.alpha_composite(base, ov)
    base = Image.alpha_composite(base, halo)
    return base.convert("RGB")


def paste_logo(img, size, cx, cy):
    """Colle le logo hexagone centré sur (cx, cy) à la taille donnée."""
    logo = logo_img.resize((size, size), Image.LANCZOS)
    x = cx - size // 2
    y = cy - size // 2
    base = img.convert("RGBA")
    base.paste(logo, (x, y), logo)
    return base.convert("RGB")


def cx_text(draw, text, y, f, color, img_w=W):
    bb = draw.textbbox((0, 0), text, font=f)
    x  = (img_w - (bb[2]-bb[0])) // 2
    draw.text((x, y), text, font=f, fill=color)


def make_video(slides_conf, audio_path, output_path, w=W, h=H):
    duration = audio_duration(audio_path)
    weights  = [c[1] for c in slides_conf]
    total_w  = sum(weights)
    parts    = []
    for i, (img, _) in enumerate(slides_conf):
        dur  = duration * weights[i] / total_w
        path = os.path.join(DIR, f"v4_slide_{i:02d}.png")
        img.save(path, "PNG")
        part = os.path.join(DIR, f"v4_part_{i:02d}.mp4")
        subprocess.run([
            FFMPEG, "-y", "-loop","1","-i", path, "-t", str(dur),
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
                   f"fade=in:0:12,fade=out:st={max(0,dur-0.5):.2f}:d=0.5",
            "-c:v","libx264","-pix_fmt","yuv420p","-r","25","-preset","fast", part
        ], capture_output=True)
        parts.append(part)
    concat = os.path.join(DIR, "v4_concat.txt")
    with open(concat, "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    tmp = os.path.join(DIR, "v4_slides.mp4")
    subprocess.run([FFMPEG,"-y","-f","concat","-safe","0","-i",concat,"-c","copy",tmp], capture_output=True)
    subprocess.run([FFMPEG,"-y","-i",tmp,"-i",audio_path,"-c:v","copy","-c:a","aac","-b:a","192k","-shortest",output_path], capture_output=True)
    for p in parts + [tmp, concat]:
        try: os.remove(p)
        except: pass


def audio_duration(path):
    res = subprocess.run([FFMPEG, "-i", path, "-f", "null", "-"], capture_output=True, text=True)
    for line in res.stderr.split("\n"):
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":"); return int(h)*3600+int(m)*60+float(s)
    return 100.0


# ══════════════════════════════════════════════════════════════════════════════
# SLIDES 16:9 (1920×1080)
# ══════════════════════════════════════════════════════════════════════════════

def slide_titre_16():
    img  = base_bg(W, H, glow_c=(0,100,120), glow_a=20)
    img  = paste_logo(img, 480, W//2, H//2 - 60)
    draw = ImageDraw.Draw(img)
    # AMAH AGENT sous le logo
    cx_text(draw, "AMAH AGENT", H//2 + 200, font(80), GOLD_B)
    cx_text(draw, "L'IA qui agit vraiment sur votre PC", H//2 + 300, font(38, False), WHITE)
    draw.rectangle([W//2-400, H//2+350, W//2+400, H//2+353], fill=(*CYAN, 120))
    cx_text(draw, "65 outils · Local · Privé · Windows 11", H//2 + 374, font(30, False), GREY)
    return img


def slide_contact_16():
    img  = base_bg(W, H, glow_c=GOLD_D, glow_a=35)
    img  = paste_logo(img, 260, W//2, H//2 - 160)
    draw = ImageDraw.Draw(img)
    cx_text(draw, "Intéressé ?", H//2 + 60, font(90), WHITE)
    cx_text(draw, "contact.amah.officiel@gmail.com", H//2 + 175, font(46, False), GOLD)
    cx_text(draw, "AMAH AGENT  ·  L'IA qui agit vraiment", H//2 + 270, font(32, False), (*CYAN, 200))
    return img


# ══════════════════════════════════════════════════════════════════════════════
# SLIDES 9:16 (1080×1920)
# ══════════════════════════════════════════════════════════════════════════════

def slide_titre_v():
    img  = base_bg(VW, VH, glow_c=(0,80,100), glow_a=20)
    img  = paste_logo(img, 600, VW//2, VH//2 - 200)
    draw = ImageDraw.Draw(img)
    cx_text(draw, "AMAH AGENT", VH//2 + 140, font(90), GOLD_B, VW)
    cx_text(draw, "L'IA qui agit vraiment", VH//2 + 250, font(44, False), WHITE, VW)
    draw.rectangle([VW//2-300, VH//2+310, VW//2+300, VH//2+313], fill=(*CYAN, 120))
    cx_text(draw, "65 outils · Local · Windows", VH//2 + 335, font(34, False), GREY, VW)
    return img


def slide_contact_v():
    img  = base_bg(VW, VH, glow_c=GOLD_D, glow_a=35)
    img  = paste_logo(img, 500, VW//2, VH//2 - 300)
    draw = ImageDraw.Draw(img)
    cx_text(draw, "Intéressé ?", VH//2 + 70, font(100), WHITE, VW)
    cx_text(draw, "contact.amah.officiel", VH//2 + 200, font(48, False), GOLD, VW)
    cx_text(draw, "@gmail.com", VH//2 + 270, font(48, False), GOLD, VW)
    cx_text(draw, "AMAH AGENT", VH//2 + 400, font(60), (*CYAN, 220), VW)
    return img


# ══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION DES VIDÉOS
# ══════════════════════════════════════════════════════════════════════════════

from video_v3_interface import (
    slide_screen, SLIDES_CONFIG as SLIDES_V3
)

MUSIC = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\music\miromaxmusic-music-promotion-no-copyright-513944.mp3"

# --- V1 : Présentation 16:9 avec logo ---
print("=== VIDEO 1 — Présentation 16:9 avec logo ===")
AUDIO_V1 = os.path.join(DIR, "amah_v2_audio.mp3")
if os.path.exists(AUDIO_V1):
    from creer_video_v2 import (
        slide_probleme, slide_solution, slide_outils, slide_tech, slide_prix
    )
    slides_v1 = [
        (slide_titre_16(),  18),
        (slide_probleme(),  14),
        (slide_solution(),  22),
        (slide_outils(),    26),
        (slide_tech(),      18),
        (slide_prix(),      18),
        (slide_contact_16(), 14),
    ]
    out_v1 = os.path.join(DIR, "amah_v4_logo.mp4")
    make_video(slides_v1, AUDIO_V1, out_v1)
    # Ajoute la musique
    out_v1_music = os.path.join(DIR, "amah_v4_logo_music.mp4")
    if os.path.exists(MUSIC):
        subprocess.run([
            FFMPEG,"-y","-i",out_v1,"-stream_loop","-1","-i",MUSIC,
            "-filter_complex","[0:a]volume=1.0[v];[1:a]volume=0.09[m];[v][m]amix=inputs=2:duration=first[out]",
            "-map","0:v","-map","[out]","-c:v","copy","-c:a","aac","-b:a","192k","-shortest",out_v1_music
        ], capture_output=True)
        os.remove(out_v1)
        os.rename(out_v1_music, out_v1)
    print(f"  OK -> {os.path.getsize(out_v1)//1024} Ko")
    os.startfile(out_v1)
else:
    print(f"  SKIP — audio manquant : {AUDIO_V1}")

# --- V2 : Interface 16:9 (remplace juste intro et contact) ---
print("=== VIDEO 2 — Interface 16:9 avec logo ===")
AUDIO_V3 = os.path.join(DIR, "amah_v2_audio.mp3")
SCR_FILES = [
    os.path.join(SCR, "screen1_accueil.png"),
    os.path.join(SCR, "screen2_email.png"),
    os.path.join(SCR, "screen3_document.png"),
    os.path.join(SCR, "screen4_navigateur.png"),
]
if all(os.path.exists(f) for f in SCR_FILES) and os.path.exists(AUDIO_V3):
    slides_v3 = [
        (slide_titre_16(),                                              12),
        (slide_screen(SCR_FILES[0],"Dites-lui ce\nque vous voulez.","Amah classe vos fichiers\nen 3 secondes.","📁 Organisation automatique"), 18),
        (slide_screen(SCR_FILES[1],"Vos emails,\nresumes.","Lire, resumer, repondre.","📧 Email Gmail integre","gauche"), 18),
        (slide_screen(SCR_FILES[2],"Creez des\ndocuments.","Word, PDF, Excel, TXT.","📄 65 types de documents"), 18),
        (slide_screen(SCR_FILES[3],"Elle navigue\npour vous.","LinkedIn, Google, n'importe quel site.","🌐 Navigation Chrome visible","gauche"), 16),
        (slide_contact_16(),                                            12),
    ]
    out_v3 = os.path.join(DIR, "amah_v4_interface_logo.mp4")
    make_video(slides_v3, AUDIO_V3, out_v3)
    if os.path.exists(MUSIC):
        out_v3_music = out_v3.replace(".mp4","_music.mp4")
        subprocess.run([
            FFMPEG,"-y","-i",out_v3,"-stream_loop","-1","-i",MUSIC,
            "-filter_complex","[0:a]volume=1.0[v];[1:a]volume=0.09[m];[v][m]amix=inputs=2:duration=first[out]",
            "-map","0:v","-map","[out]","-c:v","copy","-c:a","aac","-b:a","192k","-shortest",out_v3_music
        ], capture_output=True)
        os.remove(out_v3); os.rename(out_v3_music, out_v3)
    print(f"  OK -> {os.path.getsize(out_v3)//1024} Ko")
    os.startfile(out_v3)

# --- V3 : TikTok 9:16 avec logo ---
print("=== VIDEO 3 — TikTok 9:16 avec logo ===")
AUDIO_C3 = os.path.join(DIR, "audio_concept3.mp3")
AUDIO_C4 = os.path.join(DIR, "audio_concept4.mp3")

def slide_screen_v(screen_file, titre, sous_titre, badge=None, cote="droite"):
    """Slide vertical avec screenshot."""
    from reseaux_sociaux import vbg, cx, pill, screen_in_frame
    img  = vbg()
    scr  = screen_in_frame(screen_file, 960, 580)
    img.paste(scr, (-10, 200), scr)
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(titre.split("\n")):
        cy = 860 + i*100
        cx(draw, line, cy, font(72), (255,220,140) if line.startswith("*") else (240,235,220))
    if badge: pill(draw, badge, 1060, (0,229,255))
    return img

if os.path.exists(AUDIO_C3):
    from reseaux_sociaux import vbg, cx, pill, screen_in_frame
    slides_c3 = [
        (slide_titre_v(),             10),
        (slide_screen_v(SCR_FILES[0], "Organise\n*en 3 sec.", "47 fichiers classes.", "📁 Organisation"), 10),
        (slide_screen_v(SCR_FILES[1], "Emails\n*resumes.", "Lecture immediate.", "📧 Email Gmail", "gauche"), 10),
        (slide_screen_v(SCR_FILES[2], "Rapport\n*genere.", "30 secondes.", "📄 Word/PDF"), 8),
        (slide_contact_v(),           8),
    ]
    out_c3 = os.path.join(DIR, "concept3_v4_logo.mp4")
    make_video(slides_c3, AUDIO_C3, out_c3, VW, VH)
    if os.path.exists(MUSIC):
        out_c3m = out_c3.replace(".mp4","_music.mp4")
        subprocess.run([FFMPEG,"-y","-i",out_c3,"-stream_loop","-1","-i",MUSIC,
            "-filter_complex","[0:a]volume=1.0[v];[1:a]volume=0.09[m];[v][m]amix=inputs=2:duration=first[out]",
            "-map","0:v","-map","[out]","-c:v","copy","-c:a","aac","-b:a","192k","-shortest",out_c3m
        ], capture_output=True)
        os.remove(out_c3); os.rename(out_c3m, out_c3)
    print(f"  OK -> {os.path.getsize(out_c3)//1024} Ko")
    os.startfile(out_c3)

print("\nTERMINE — 3 vidéos avec le logo hexagone !")
