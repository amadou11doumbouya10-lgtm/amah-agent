"""
Tout pour les réseaux sociaux :
1. Conversion v1 et v3 en 9:16
2. Concept 3 — TikTok Hook "Regardez ça"
3. Concept 4 — Avant/Après
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess, os, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FFMPEG = r"C:\Users\Smarte technologui\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
DIR    = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
SCR    = os.path.join(DIR, "screens")
API_KEY  = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "cjVigY5qzO86Huf0OWal"
HEADERS  = {"xi-api-key": API_KEY, "Content-Type": "application/json"}

VW, VH = 1080, 1920  # 9:16 vertical

BG     = (8,   7,   5)
GOLD   = (212, 180, 110)
GOLD_B = (255, 220, 140)
GOLD_D = (90,  68,  28)
WHITE  = (240, 235, 220)
GREY   = (130, 125, 110)
RED    = (220, 60,  60)
GREEN  = (80,  200, 100)
DARK   = (20,  18,  12)


def font(size, bold=True):
    for n in (["arialbd.ttf","calibrib.ttf"] if bold else ["arial.ttf","calibri.ttf"]):
        try: return ImageFont.truetype(f"C:/Windows/Fonts/{n}", size)
        except: pass
    return ImageFont.load_default(size=size)


def vbg(glow_c=GOLD_D, glow_a=30):
    img = Image.new("RGB", (VW, VH), BG)
    ov  = Image.new("RGBA", (VW, VH), (0,0,0,0))
    d   = ImageDraw.Draw(ov)
    for x in range(0, VW, 80): d.line([(x,0),(x,VH)], fill=(*GOLD_D, 8), width=1)
    for y in range(0, VH, 80): d.line([(0,y),(VW,y)], fill=(*GOLD_D, 8), width=1)
    halo = Image.new("RGBA", (VW, VH), (0,0,0,0))
    hd   = ImageDraw.Draw(halo)
    hd.ellipse([VW//2-500, VH//2-600, VW//2+500, VH//2+600], fill=(*glow_c, glow_a))
    halo = halo.filter(ImageFilter.GaussianBlur(120))
    base = img.convert("RGBA")
    base = Image.alpha_composite(base, ov)
    base = Image.alpha_composite(base, halo)
    return base.convert("RGB")


def cx(draw, text, y, f, color=WHITE):
    bb = draw.textbbox((0,0), text, font=f)
    x  = (VW - (bb[2]-bb[0])) // 2
    draw.text((x, y), text, font=f, fill=color)
    return bb[3]-bb[1]


def pill(draw, text, y, color=GOLD, bg_a=50):
    f  = font(30, False)
    bb = draw.textbbox((0,0), text, font=f)
    tw = bb[2]-bb[0]
    x  = (VW - tw - 40) // 2
    draw.rounded_rectangle([x-5, y-8, x+tw+45, y+40], radius=20, fill=(*color[:3], bg_a))
    draw.text((x+20, y), text, font=f, fill=color)


def screen_in_frame(screen_file, target_w=960, target_h=580):
    """Screenshot dans cadre fenêtre pour format vertical."""
    scr = Image.open(screen_file).convert("RGBA").resize((target_w, target_h), Image.LANCZOS)
    fw, fh = target_w + 20, target_h + 44
    frame  = Image.new("RGBA", (fw, fh), (0,0,0,0))
    fd     = ImageDraw.Draw(frame)
    # Ombre
    shadow = Image.new("RGBA", (fw+30, fh+30), (0,0,0,0))
    sd     = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([10,14,fw+10,fh+14], radius=14, fill=(0,0,0,100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    out    = Image.new("RGBA", (fw+30, fh+30), (0,0,0,0))
    out.paste(shadow, (0,0), shadow)
    fd2    = ImageDraw.Draw(out)
    fd2.rounded_rectangle([10,10,fw+10,fh+10], radius=14, fill=(22,20,14,255))
    fd2.rounded_rectangle([10,10,fw+10,54+10], radius=14, fill=(32,30,22,255))
    for bx, bc in [(30,(237,95,85,255)),(56,(242,188,50,255)),(82,(100,200,86,255))]:
        fd2.ellipse([bx,24,bx+14,38], fill=bc)
    out.paste(scr, (20, 54), scr)
    return out


def tts(script, filename):
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        headers=HEADERS,
        json={"text": script, "model_id": "eleven_multilingual_v2",
              "voice_settings": {"stability":0.52,"similarity_boost":0.82,"style":0.25,"use_speaker_boost":True}}
    )
    if r.status_code == 200:
        with open(filename, "wb") as f: f.write(r.content)
        return True
    return False


def audio_duration(path):
    res = subprocess.run([FFMPEG, "-i", path, "-f", "null", "-"], capture_output=True, text=True)
    for line in res.stderr.split("\n"):
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":"); return int(h)*3600+int(m)*60+float(s)
    return 60.0


def make_video(slides_conf, audio_path, output_path, w=VW, h=VH):
    duration = audio_duration(audio_path)
    weights  = [c[1] for c in slides_conf]
    total_w  = sum(weights)
    parts    = []
    for i, (img, _) in enumerate(slides_conf):
        dur  = duration * weights[i] / total_w
        path = os.path.join(DIR, f"tmp_slide_{i:02d}.png")
        img.save(path, "PNG")
        part = os.path.join(DIR, f"tmp_part_{i:02d}.mp4")
        subprocess.run([
            FFMPEG, "-y", "-loop","1","-i", path,"-t",str(dur),
            "-vf",f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fade=in:0:10,fade=out:st={max(0,dur-0.4):.2f}:d=0.4",
            "-c:v","libx264","-pix_fmt","yuv420p","-r","25","-preset","fast", part
        ], capture_output=True)
        parts.append(part)
    concat = os.path.join(DIR, "tmp_concat.txt")
    with open(concat,"w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    tmp = os.path.join(DIR, "tmp_slides.mp4")
    subprocess.run([FFMPEG,"-y","-f","concat","-safe","0","-i",concat,"-c","copy",tmp], capture_output=True)
    subprocess.run([FFMPEG,"-y","-i",tmp,"-i",audio_path,"-c:v","copy","-c:a","aac","-b:a","192k","-shortest",output_path], capture_output=True)
    for p in parts + [tmp, concat]:
        try: os.remove(p)
        except: pass


# ══════════════════════════════════════════════════════════════════════════════
# 1 & 2 — CONVERSION DES VIDÉOS EXISTANTES EN 9:16
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("CONVERSION v1 et v3 en format 9:16")
print("=" * 60)

for src, dst in [
    (os.path.join(DIR,"amah_presentation.mp4"), os.path.join(DIR,"amah_v1_9x16.mp4")),
    (os.path.join(DIR,"amah_v3_interface.mp4"), os.path.join(DIR,"amah_v3_9x16.mp4")),
]:
    if os.path.exists(src):
        print(f"  Conversion : {os.path.basename(src)} -> {os.path.basename(dst)}")
        subprocess.run([
            FFMPEG, "-y", "-i", src,
            "-vf", f"scale=1080:608,pad=1080:1920:0:656:black",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "copy", dst
        ], capture_output=True)
        print(f"  OK — {os.path.getsize(dst)//1024} Ko")


# ══════════════════════════════════════════════════════════════════════════════
# CONCEPT 3 — TikTok Hook "Regardez ça" (30 secondes, percutant)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("CONCEPT 3 — TikTok Hook")
print("="*60)

SCRIPT_3 = """
Regardez ce que fait mon IA en 3 secondes.

Je lui dis : organise mon bureau. Et voilà. Tout classé.

Je lui demande mes emails. Elle les lit.

Je veux un rapport Word. Il est prêt.

Soixante-cinq choses qu'Amah fait pour vous. Automatiquement. Sur votre PC. Vos données restent chez vous.

Linkez en bio. contact.amah.officiel@gmail.com
""".strip()

audio3 = os.path.join(DIR, "audio_concept3.mp3")
print("  Génération audio...")
tts(SCRIPT_3, audio3)

def make_hook_slides():
    slides = []

    # Slide 0 — Hook accrocheur
    img  = vbg(glow_c=(180,50,50), glow_a=25)
    draw = ImageDraw.Draw(img)
    pill(draw, "🔥 LE TRUC QUI CHANGE TOUT", 160, RED)
    cx(draw, "Regardez", 280, font(110), WHITE)
    cx(draw, "ce que fait", 410, font(110), WHITE)
    cx(draw, "mon IA.", 540, font(110), GOLD_B)
    cx(draw, "En 3 secondes.", 720, font(70, False), GREY)
    slides.append((img, 8))

    # Slide 1 — Screenshot organisation
    img  = vbg()
    draw = ImageDraw.Draw(img)
    pill(draw, "\"Organise mon bureau\"", 100, GOLD)
    scr  = screen_in_frame(os.path.join(SCR,"screen1_accueil.png"), 1000, 600)
    img.paste(scr, (-10, 190), scr)
    draw = ImageDraw.Draw(img)
    cx(draw, "47 fichiers classés.", 840, font(72), WHITE)
    cx(draw, "3 secondes.", 940, font(72), GOLD_B)
    slides.append((img, 10))

    # Slide 2 — Screenshot emails
    img  = vbg()
    draw = ImageDraw.Draw(img)
    pill(draw, "\"Lis mes emails\"", 100, GOLD)
    scr  = screen_in_frame(os.path.join(SCR,"screen2_email.png"), 1000, 600)
    img.paste(scr, (-10, 190), scr)
    draw = ImageDraw.Draw(img)
    cx(draw, "Résumé complet.", 840, font(72), WHITE)
    cx(draw, "Réponse prête.", 940, font(72), GOLD_B)
    slides.append((img, 10))

    # Slide 3 — Chiffres chocs
    img  = vbg(glow_c=GOLD_D, glow_a=40)
    draw = ImageDraw.Draw(img)
    pill(draw, "⚡ AMAH AGENT", 200, GOLD)
    cx(draw, "65", 360, font(280), GOLD_B)
    cx(draw, "outils intégrés", 640, font(60, False), WHITE)
    cx(draw, "Sur votre PC.", 780, font(56, False), GREY)
    cx(draw, "Vos données restent", 880, font(56, False), GREY)
    cx(draw, "chez vous.", 960, font(56, False), GREY)
    slides.append((img, 8))

    # Slide 4 — CTA
    img  = vbg(glow_c=GOLD_D, glow_a=35)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, VW, 8], fill=GOLD)
    draw.rectangle([0, VH-8, VW, VH], fill=GOLD)
    cx(draw, "Intéressé ?", 420, font(100), WHITE)
    cx(draw, "contact.amah", 580, font(54, False), GOLD)
    cx(draw, ".officiel@gmail.com", 650, font(54, False), GOLD)
    cx(draw, "Lien en bio 👇", 820, font(50, False), GREY)
    pill(draw, "AMAH AGENT · L'IA qui agit", 1000, GOLD)
    slides.append((img, 6))

    return slides

slides3 = make_hook_slides()
out3    = os.path.join(DIR, "concept3_tiktok_hook.mp4")
print("  Assemblage vidéo...")
make_video(slides3, audio3, out3)
print(f"  OK — {os.path.getsize(out3)//1024} Ko")


# ══════════════════════════════════════════════════════════════════════════════
# CONCEPT 4 — Avant / Après (comparaison émotionnelle)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("CONCEPT 4 — Avant / Après")
print("="*60)

SCRIPT_4 = """
Avant Amah.

Je passe deux heures à classer mes fichiers.
Je cherche l'email de lundi pendant dix minutes.
Je rédige un rapport pendant une heure.

Avec Amah.

Fichiers classés. Trois secondes.
Email trouvé. Cinq secondes.
Rapport généré. Trente secondes.

C'est ça la différence.

Amah Agent. L'IA qui agit vraiment. contact.amah.officiel@gmail.com
""".strip()

audio4 = os.path.join(DIR, "audio_concept4.mp3")
print("  Génération audio...")
tts(SCRIPT_4, audio4)

def make_avantapres_slides():
    slides = []

    # Slide 0 — Accroche
    img  = vbg(glow_c=(180,50,50), glow_a=20)
    draw = ImageDraw.Draw(img)
    cx(draw, "Avant Amah.", 500, font(120), WHITE)
    cx(draw, "😩", 680, font(120), WHITE)
    slides.append((img, 8))

    # Slide 1 — Avant (rouge, douloureux)
    img  = Image.new("RGB", (VW, VH), (18,5,5))
    ov   = Image.new("RGBA", (VW, VH),(0,0,0,0))
    halo = Image.new("RGBA", (VW, VH),(0,0,0,0))
    hd   = ImageDraw.Draw(halo)
    hd.ellipse([VW//2-400, VH//2-500, VW//2+400, VH//2+500], fill=(*RED, 20))
    halo = halo.filter(ImageFilter.GaussianBlur(100))
    img  = Image.alpha_composite(img.convert("RGBA"), halo).convert("RGB")
    draw = ImageDraw.Draw(img)
    pill(draw, "❌ AVANT AMAH", 180, RED)
    tasks = [
        ("Classer les fichiers", "2 heures"),
        ("Chercher un email", "10 minutes"),
        ("Rédiger un rapport", "1 heure"),
    ]
    y = 360
    for task, time in tasks:
        draw.rounded_rectangle([60, y, VW-60, y+160], radius=16, fill=(30,10,10,200))
        draw.text((100, y+20), "❌  " + task, font=font(44), fill=(220,180,180))
        draw.text((100, y+90), "     " + time + " perdues", font=font(36, False), fill=RED)
        y += 190
    slides.append((img, 12))

    # Slide 2 — Transition
    img  = vbg(glow_c=GOLD_D, glow_a=40)
    draw = ImageDraw.Draw(img)
    cx(draw, "Avec Amah.", 500, font(120), GOLD_B)
    cx(draw, "✨", 680, font(120), WHITE)
    slides.append((img, 6))

    # Slide 3 — Après (vert, victoire)
    img  = Image.new("RGB", (VW, VH), (5,15,5))
    halo = Image.new("RGBA", (VW, VH),(0,0,0,0))
    hd   = ImageDraw.Draw(halo)
    hd.ellipse([VW//2-400, VH//2-500, VW//2+400, VH//2+500], fill=(*GREEN, 20))
    halo = halo.filter(ImageFilter.GaussianBlur(100))
    img  = Image.alpha_composite(img.convert("RGBA"), halo).convert("RGB")
    draw = ImageDraw.Draw(img)
    pill(draw, "✅ AVEC AMAH", 180, GREEN)
    afters = [
        ("Fichiers classés", "3 secondes"),
        ("Email trouvé", "5 secondes"),
        ("Rapport généré", "30 secondes"),
    ]
    y = 360
    for task, time in afters:
        draw.rounded_rectangle([60, y, VW-60, y+160], radius=16, fill=(10,30,10,200))
        draw.text((100, y+20), "✅  " + task, font=font(44), fill=(180,240,180))
        draw.text((100, y+90), "     " + time + " seulement !", font=font(36, False), fill=GREEN)
        y += 190
    slides.append((img, 14))

    # Slide 4 — Screenshot interface + chiffre
    img  = vbg()
    draw = ImageDraw.Draw(img)
    scr  = screen_in_frame(os.path.join(SCR,"screen3_document.png"), 1000, 580)
    img.paste(scr, (-10, 140), scr)
    draw = ImageDraw.Draw(img)
    pill(draw, "65 outils intégrés", 780, GOLD)
    cx(draw, "Sur votre PC.", 890, font(60, False), WHITE)
    cx(draw, "Vos données restent", 980, font(54, False), GREY)
    cx(draw, "chez vous.", 1060, font(54, False), GREY)
    slides.append((img, 10))

    # Slide 5 — CTA final
    img  = vbg(glow_c=GOLD_D, glow_a=40)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0,0,VW,8], fill=GOLD)
    draw.rectangle([0,VH-8,VW,VH], fill=GOLD)
    cx(draw, "C'est ça", 360, font(100), WHITE)
    cx(draw, "la différence.", 480, font(100), GOLD_B)
    cx(draw, "AMAH AGENT", 680, font(80), GOLD)
    cx(draw, "contact.amah.officiel", 820, font(46, False), GOLD)
    cx(draw, "@gmail.com", 890, font(46, False), GOLD)
    pill(draw, "L'IA qui agit vraiment 🚀", 1020, GOLD)
    slides.append((img, 8))

    return slides

slides4 = make_avantapres_slides()
out4    = os.path.join(DIR, "concept4_avant_apres.mp4")
print("  Assemblage vidéo...")
make_video(slides4, audio4, out4)
print(f"  OK — {os.path.getsize(out4)//1024} Ko")


# ══════════════════════════════════════════════════════════════════════════════
# RÉSUMÉ
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("FICHIERS CRÉÉS :")
files = [
    ("amah_v1_9x16.mp4",         "V1 convertie en 9:16"),
    ("amah_v3_9x16.mp4",         "V3 interface convertie en 9:16"),
    ("concept3_tiktok_hook.mp4", "Concept 3 — TikTok Hook"),
    ("concept4_avant_apres.mp4", "Concept 4 — Avant/Après"),
]
for fname, desc in files:
    path = os.path.join(DIR, fname)
    if os.path.exists(path):
        print(f"  ✓ {fname:35} {os.path.getsize(path)//1024:5} Ko — {desc}")
        os.startfile(path)
print("="*60)

