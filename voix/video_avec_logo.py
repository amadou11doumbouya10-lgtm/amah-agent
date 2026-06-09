"""
Génère les vidéos avec le logo hexagone — utilise les audios existants.
Aucun appel ElevenLabs nécessaire.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess, os

FFMPEG = r"C:\Users\Smarte technologui\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
DIR    = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
LOGO   = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\amah_logo_hex.png"
SCR    = os.path.join(DIR, "screens")
MUSIC  = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\music\miromaxmusic-music-promotion-no-copyright-513944.mp3"

W, H   = 1920, 1080
VW, VH = 1080, 1920

BG   = (8, 7, 5); GOLD = (212,180,110); GOLD_B=(255,220,140)
GOLD_D=(90,68,28); WHITE=(240,235,220); GREY=(130,125,110); CYAN=(0,229,255)

logo_src = Image.open(LOGO).convert("RGBA")


def font(size, bold=True):
    for n in (["arialbd.ttf","calibrib.ttf"] if bold else ["arial.ttf","calibri.ttf"]):
        try: return ImageFont.truetype(f"C:/Windows/Fonts/{n}", size)
        except: pass
    return ImageFont.load_default(size=size)


def base(w=W, h=H):
    img = Image.new("RGB", (w, h), BG)
    ov  = Image.new("RGBA", (w, h), (0,0,0,0))
    d   = ImageDraw.Draw(ov)
    for x in range(0,w,100): d.line([(x,0),(x,h)], fill=(*GOLD_D,8), width=1)
    for y in range(0,h,100): d.line([(0,y),(w,y)], fill=(*GOLD_D,8), width=1)
    halo = Image.new("RGBA",(w,h),(0,0,0,0))
    hd   = ImageDraw.Draw(halo)
    hd.ellipse([w//2-500,h//2-400,w//2+500,h//2+400], fill=(*GOLD_D,25))
    halo = halo.filter(ImageFilter.GaussianBlur(100))
    b    = img.convert("RGBA")
    b    = Image.alpha_composite(b, ov)
    b    = Image.alpha_composite(b, halo)
    return b.convert("RGB")


def logo(img, size, cx, cy):
    l = logo_src.resize((size,size), Image.LANCZOS)
    b = img.convert("RGBA")
    b.paste(l, (cx-size//2, cy-size//2), l)
    return b.convert("RGB")


def cx_text(draw, text, y, f, color, w=W):
    bb = draw.textbbox((0,0), text, font=f)
    draw.text(((w-(bb[2]-bb[0]))//2, y), text, font=f, fill=color)


# ── SLIDES 16:9 ───────────────────────────────────────────────────────────────

def titre_16():
    img  = base(W, H)
    img  = logo(img, 460, W//2, H//2-80)
    draw = ImageDraw.Draw(img)
    cx_text(draw, "AMAH AGENT", H//2+195, font(80), GOLD_B)
    cx_text(draw, "L'IA qui agit vraiment sur votre PC", H//2+295, font(38,False), WHITE)
    draw.rectangle([W//2-350,H//2+348,W//2+350,H//2+351], fill=(*CYAN,120))
    cx_text(draw, "65 outils  ·  Local  ·  Prive  ·  Windows 11", H//2+368, font(28,False), GREY)
    return img


def contact_16():
    img  = base(W, H)
    img  = logo(img, 240, W//2, H//2-180)
    draw = ImageDraw.Draw(img)
    cx_text(draw, "Interesse ?", H//2+50, font(90), WHITE)
    cx_text(draw, "contact.amah.officiel@gmail.com", H//2+165, font(44,False), GOLD)
    cx_text(draw, "AMAH AGENT  ·  L'IA qui agit vraiment", H//2+258, font(30,False), (*CYAN,200))
    return img


def screen_slide(screen_file, titre_g, sous_t, badge=None, cote="droite"):
    img  = base(W, H)
    scr  = Image.open(screen_file).convert("RGBA")
    sw   = 860; sh = int(scr.height*sw/scr.width)
    scr  = scr.resize((sw,sh), Image.LANCZOS)
    # Cadre fenêtre
    fw,fh = sw+20,sh+44
    frm   = Image.new("RGBA",(fw+30,fh+30),(0,0,0,0))
    fd    = ImageDraw.Draw(frm)
    fd.rounded_rectangle([10,14,fw+10,fh+14], radius=14, fill=(0,0,0,100))
    shadow = frm.filter(ImageFilter.GaussianBlur(10))
    out    = Image.new("RGBA",(fw+30,fh+30),(0,0,0,0))
    out.paste(shadow,(0,0),shadow)
    fd2    = ImageDraw.Draw(out)
    fd2.rounded_rectangle([10,10,fw+10,fh+10], radius=14, fill=(22,20,14,255))
    fd2.rounded_rectangle([10,10,fw+10,54+10], radius=14, fill=(32,30,22,255))
    for bx,bc in [(30,(237,95,85,255)),(56,(242,188,50,255)),(82,(100,200,86,255))]:
        fd2.ellipse([bx,24,bx+14,38], fill=bc)
    out.paste(scr,(20,54),scr)
    if cote=="droite":
        fx=W-fw-40; tx=80
    else:
        fx=-10; tx=sw+80
    base2 = img.convert("RGBA")
    base2.paste(out,(fx,(H-fh)//2-20),out)
    img   = base2.convert("RGB")
    draw  = ImageDraw.Draw(img)
    lines = titre_g.split("\n")
    ty    = H//2 - len(lines)*45 - 30
    ft    = font(66)
    for line in lines:
        cx_text(draw, line.lstrip("*"), ty, ft, GOLD_B if line.startswith("*") else WHITE, W)
        ty += 90
    cx_text(draw, sous_t, ty+10, font(32,False), GREY, W)
    if badge:
        bb = draw.textbbox((0,0),badge,font=font(26,False))
        bw = bb[2]-bb[0]+30; bx=(W-bw)//2; by=ty+55
        draw.rounded_rectangle([bx-5,by-6,bx+bw+5,by+36], radius=14, fill=(*CYAN,40))
        draw.text((bx+10,by), badge, font=font(26,False), fill=(*CYAN,220))
    return img


# ── SLIDES 9:16 ───────────────────────────────────────────────────────────────

def titre_v():
    img  = base(VW,VH)
    img  = logo(img, 580, VW//2, VH//2-220)
    draw = ImageDraw.Draw(img)
    cx_text(draw,"AMAH AGENT",VH//2+150,font(86),GOLD_B,VW)
    cx_text(draw,"L'IA qui agit vraiment",VH//2+258,font(42,False),WHITE,VW)
    draw.rectangle([VW//2-280,VH//2+318,VW//2+280,VH//2+321],fill=(*CYAN,120))
    cx_text(draw,"65 outils  ·  Local  ·  Windows",VH//2+342,font(32,False),GREY,VW)
    return img


def contact_v():
    img  = base(VW,VH)
    img  = logo(img, 460, VW//2, VH//2-330)
    draw = ImageDraw.Draw(img)
    cx_text(draw,"Interesse ?",VH//2+50,font(100),WHITE,VW)
    cx_text(draw,"contact.amah.officiel",VH//2+185,font(46,False),GOLD,VW)
    cx_text(draw,"@gmail.com",VH//2+255,font(46,False),GOLD,VW)
    cx_text(draw,"AMAH AGENT",VH//2+390,font(58),(*CYAN,220),VW)
    return img


# ── ASSEMBLAGE ────────────────────────────────────────────────────────────────

def dur(audio):
    res = subprocess.run([FFMPEG,"-i",audio,"-f","null","-"],capture_output=True,text=True)
    for l in res.stderr.split("\n"):
        if "Duration:" in l:
            t=l.split("Duration:")[1].split(",")[0].strip(); h,m,s=t.split(":")
            return int(h)*3600+int(m)*60+float(s)
    return 90.0


def make(slides, audio, out, w=W, h=H, with_music=True):
    d  = dur(audio)
    ws = [s[1] for s in slides]; tw = sum(ws)
    parts=[]
    for i,(img,_) in enumerate(slides):
        dd  = d*ws[i]/tw
        pp  = os.path.join(DIR,f"_s{i}.png"); img.save(pp,"PNG")
        mp  = os.path.join(DIR,f"_p{i}.mp4")
        subprocess.run([FFMPEG,"-y","-loop","1","-i",pp,"-t",str(dd),
            "-vf",f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fade=in:0:12,fade=out:st={max(0,dd-0.5):.2f}:d=0.5",
            "-c:v","libx264","-pix_fmt","yuv420p","-r","25","-preset","fast",mp],capture_output=True)
        parts.append(mp); os.remove(pp)
    cf=os.path.join(DIR,"_concat.txt")
    with open(cf,"w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    tmp=os.path.join(DIR,"_tmp.mp4")
    subprocess.run([FFMPEG,"-y","-f","concat","-safe","0","-i",cf,"-c","copy",tmp],capture_output=True)
    if with_music and os.path.exists(MUSIC):
        # 3 entrées : vidéo (pas d'audio) + voix + musique
        subprocess.run([
            FFMPEG,"-y",
            "-i",tmp,                    # 0 : vidéo slides (pas d'audio)
            "-i",audio,                  # 1 : voix off
            "-stream_loop","-1","-i",MUSIC, # 2 : musique en boucle
            "-filter_complex",
            "[1:a]volume=1.0[v];[2:a]volume=0.09[m];[v][m]amix=inputs=2:duration=shortest[ao]",
            "-map","0:v","-map","[ao]",
            "-c:v","copy","-c:a","aac","-b:a","192k","-shortest",out
        ], capture_output=True)
    else:
        subprocess.run([FFMPEG,"-y","-i",tmp,"-i",audio,
                        "-c:v","copy","-c:a","aac","-b:a","192k","-shortest",out],
                       capture_output=True)
    for p in parts+[tmp,cf]:
        try: os.remove(p)
        except: pass


SCR1 = os.path.join(SCR,"screen1_accueil.png")
SCR2 = os.path.join(SCR,"screen2_email.png")
SCR3 = os.path.join(SCR,"screen3_document.png")
SCR4 = os.path.join(SCR,"screen4_navigateur.png")

# ── VIDEO 1 — Présentation 16:9 ────────────────────────────────────────────────
AUDIO1 = os.path.join(DIR,"amah_v2_audio.mp3")
if os.path.exists(AUDIO1):
    print("Video 1 — Presentation 16:9 avec logo...")
    slides1 = [
        (titre_16(), 14),
        (screen_slide(SCR1,"Dites-lui ce que\n*vous voulez.","Amah classe en 3 secondes.","📁 Organisation automatique"), 18),
        (screen_slide(SCR2,"Vos emails,\n*resumes.","Lire, resumer, repondre.","📧 Email Gmail","gauche"), 16),
        (screen_slide(SCR3,"Creez des\n*documents.","Word, PDF, Excel, TXT.","📄 Generes automatiquement"), 16),
        (screen_slide(SCR4,"Elle navigue\n*pour vous.","Tout site, elle lis et resume.","🌐 Navigation Chrome","gauche"), 14),
        (contact_16(), 12),
    ]
    out1 = os.path.join(DIR,"amah_v4_logo.mp4")
    make(slides1, AUDIO1, out1)
    print(f"  OK -> {os.path.getsize(out1)//1024} Ko")
    os.startfile(out1)

# ── VIDEO 2 — TikTok 9:16 ──────────────────────────────────────────────────────
AUDIO2 = os.path.join(DIR,"audio_concept3.mp3")
if os.path.exists(AUDIO2):
    print("Video 2 — TikTok 9:16 avec logo...")
    slides2 = [
        (titre_v(), 10),
        (screen_slide(SCR1,"Organise\n*en 3 sec.","47 fichiers classes.","📁 Automatique") if os.path.exists(SCR1) else titre_v(), 10),
        (screen_slide(SCR2,"Emails\n*resumes.","Lecture immediate.","📧 Gmail","gauche") if os.path.exists(SCR2) else titre_v(), 10),
        (screen_slide(SCR3,"Rapport\n*genere.","30 secondes.","📄 Word/PDF") if os.path.exists(SCR3) else titre_v(), 8),
        (contact_v(), 8),
    ]
    out2 = os.path.join(DIR,"concept3_v4_logo.mp4")
    make(slides2, AUDIO2, out2, VW, VH)
    print(f"  OK -> {os.path.getsize(out2)//1024} Ko")
    os.startfile(out2)

# ── VIDEO 3 — Avant/Après 9:16 ─────────────────────────────────────────────────
AUDIO3 = os.path.join(DIR,"audio_concept4.mp3")
if os.path.exists(AUDIO3):
    print("Video 3 — Avant/Apres 9:16 avec logo...")
    slides3 = [
        (titre_v(), 10),
        (contact_v(), 8),
    ]
    out3 = os.path.join(DIR,"concept4_v4_logo.mp4")
    make(slides3, AUDIO3, out3, VW, VH)
    print(f"  OK -> {os.path.getsize(out3)//1024} Ko")
    os.startfile(out3)

print("\nTERMINE !")
