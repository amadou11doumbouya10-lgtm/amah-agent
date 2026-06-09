"""
Ajout de texte aux vidéos :
- Option 1 (sous-titres TikTok) : concept3, concept4, amah_v3_9x16
- Option 2 (mots-clés d'accroche) : amah_v1, amah_v3, amah_v1_9x16
"""
import subprocess, os

FFMPEG = r"C:\Users\Smarte technologui\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
DIR    = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
FONT   = r"C\:/Windows/Fonts/arialbd.ttf"  # FFmpeg utilise / et pas \\


def srt(entries, path):
    """Crée un fichier SRT depuis une liste de (start, end, text)."""
    def ts(s):
        h = int(s//3600); m = int((s%3600)//60); sec = s%60
        return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")
    with open(path, "w", encoding="utf-8") as f:
        for i, (s, e, t) in enumerate(entries, 1):
            f.write(f"{i}\n{ts(s)} --> {ts(e)}\n{t}\n\n")


def burn_srt(src, srt_path, dst, font_size=62, is_vertical=False):
    """Brûle les sous-titres dans la vidéo (style TikTok centré)."""
    fs = font_size if not is_vertical else 72
    style = (
        f"Fontname=Arial,Fontsize={fs},Bold=1,"
        "PrimaryColour=&H00FFFFFF,"   # blanc
        "OutlineColour=&H00000000,"   # contour noir
        "Outline=3,Shadow=2,"
        "Alignment=2,"                # centré en bas
        "MarginV=80"
    )
    subprocess.run([
        FFMPEG, "-y", "-i", src,
        "-vf", f"subtitles='{srt_path.replace(chr(92), '/')}':force_style='{style}'",
        "-c:a", "copy", dst
    ], capture_output=True)


def add_keywords(src, dst, keywords, is_vertical=False):
    """
    Ajoute des mots-clés qui apparaissent/disparaissent (Option 2).
    keywords: liste de (start, end, text, couleur)
    """
    filters = []
    for start, end, text, color in keywords:
        dur    = end - start
        fade_d = min(0.4, dur / 3)
        alpha  = (
            f"if(lt(t-{start},{fade_d}),(t-{start})/{fade_d},"
            f"if(lt(t,{end}-{fade_d}),1,"
            f"({end}-t)/{fade_d}))"
        )
        fs = 72 if is_vertical else 58
        y  = "(h-text_h)/2" if is_vertical else "h*0.82"
        filters.append(
            f"drawtext=fontfile='{FONT}':text='{text}':"
            f"fontcolor='{color}':fontsize={fs}:bold=1:"
            f"x=(w-text_w)/2:y={y}:"
            f"bordercolor=black:borderw=3:"
            f"alpha='{alpha}':enable='between(t,{start},{end})'"
        )
    vf = ",".join(filters) if filters else "null"
    subprocess.run([
        FFMPEG, "-y", "-i", src,
        "-vf", vf,
        "-c:a", "copy", dst
    ], capture_output=True)


# ══════════════════════════════════════════════════════════════════════════════
# OPTION 1 — Sous-titres TikTok
# ══════════════════════════════════════════════════════════════════════════════

# Concept 3 — TikTok Hook (~45 secondes)
print("Sous-titres : concept3...")
srt3 = [
    (0.0,  3.0,  "Regardez ce que fait mon IA"),
    (3.0,  5.0,  "en 3 secondes."),
    (5.5,  9.0,  "Je lui dis :\nOrganise mon bureau."),
    (9.0,  12.5, "Et voilà. Tout classé. ✅"),
    (13.0, 16.5, "Je lui demande mes emails."),
    (16.5, 19.0, "Elle les lit. 📧"),
    (19.5, 22.5, "Je veux un rapport Word."),
    (22.5, 25.0, "Il est prêt. 📄"),
    (25.5, 30.0, "65 choses qu'Amah fait pour vous."),
    (30.0, 34.0, "Automatiquement."),
    (34.5, 38.5, "Sur votre PC.\nVos données restent chez vous. 🔒"),
    (39.0, 43.0, "contact.amah.officiel@gmail.com"),
    (43.0, 46.0, "AMAH AGENT 🚀"),
]
srt_path3 = os.path.join(DIR, "subs_concept3.srt")
srt(srt3, srt_path3)
burn_srt(
    os.path.join(DIR, "concept3_music.mp4"),
    srt_path3,
    os.path.join(DIR, "concept3_final.mp4"),
    is_vertical=True
)
print("  OK -> concept3_final.mp4")

# Concept 4 — Avant/Après (~55 secondes)
print("Sous-titres : concept4...")
srt4 = [
    (0.0,  3.5,  "Avant Amah. 😩"),
    (4.0,  8.5,  "2 heures pour classer mes fichiers."),
    (9.0,  13.0, "10 minutes pour trouver un email."),
    (13.5, 17.5, "1 heure pour rédiger un rapport."),
    (18.5, 22.0, "Avec Amah. ✨"),
    (22.5, 26.0, "Fichiers classés.\n3 secondes. ✅"),
    (26.5, 30.0, "Email trouvé.\n5 secondes. ✅"),
    (30.5, 34.0, "Rapport généré.\n30 secondes. ✅"),
    (35.0, 39.0, "C'est ça la différence."),
    (39.5, 44.0, "AMAH AGENT"),
    (44.5, 50.0, "L'IA qui agit vraiment."),
    (50.5, 55.0, "contact.amah.officiel@gmail.com 📩"),
]
srt_path4 = os.path.join(DIR, "subs_concept4.srt")
srt(srt4, srt_path4)
burn_srt(
    os.path.join(DIR, "concept4_music.mp4"),
    srt_path4,
    os.path.join(DIR, "concept4_final.mp4"),
    is_vertical=True
)
print("  OK -> concept4_final.mp4")

# amah_v3_9x16 — sous-titres courts version verticale
print("Sous-titres : amah_v3_9x16...")
srt_v3 = [
    (0.0,   6.0,  "Un assistant IA sur votre PC."),
    (6.5,  13.0,  "\"Organise mon bureau\"\n→ 47 fichiers classés en 3s"),
    (13.5, 22.0,  "\"Lis mes emails\"\n→ Résumé immédiat 📧"),
    (22.5, 32.0,  "\"Crée un rapport Word\"\n→ Généré automatiquement 📄"),
    (32.5, 42.0,  "\"Ouvre LinkedIn\"\n→ Elle lit et résume 🌐"),
    (43.0, 50.0,  "65 outils. 100% local.\nVos données restent chez vous. 🔒"),
    (50.5, 58.0,  "contact.amah.officiel@gmail.com"),
    (58.5, 64.0,  "AMAH AGENT 🚀"),
]
srt_path_v3 = os.path.join(DIR, "subs_v3_9x16.srt")
srt(srt_v3, srt_path_v3)
burn_srt(
    os.path.join(DIR, "amah_v3_9x16_music.mp4"),
    srt_path_v3,
    os.path.join(DIR, "amah_v3_9x16_final.mp4"),
    is_vertical=True
)
print("  OK -> amah_v3_9x16_final.mp4")


# ══════════════════════════════════════════════════════════════════════════════
# OPTION 2 — Mots-clés d'accroche
# ══════════════════════════════════════════════════════════════════════════════

# amah_v1 (16:9) — mots-clés dorés
print("Mots-cles : amah_v1...")
kw_v1 = [
    (8,  14, "Imaginez...",       "white"),
    (15, 22, "L'IA qui AGIT",    "#D4B46E"),
    (28, 36, "\"Organise mon bureau\"",  "white"),
    (37, 44, "3 SECONDES ⚡",    "#D4B46E"),
    (50, 58, "65 OUTILS",        "#D4B46E"),
    (59, 67, "100% LOCAL 🔒",    "white"),
    (68, 76, "Mémoire persistante 🧠", "#D4B46E"),
    (82, 90, "AMAH AGENT",       "#D4B46E"),
]
add_keywords(
    os.path.join(DIR, "amah_v1_music.mp4"),
    os.path.join(DIR, "amah_v1_final.mp4"),
    kw_v1, is_vertical=False
)
print("  OK -> amah_v1_final.mp4")

# amah_v3 (16:9 interface) — mots-clés
print("Mots-cles : amah_v3...")
kw_v3 = [
    (5,  13, "Dites-lui ce que vous voulez.", "white"),
    (14, 22, "Elle le fait. ✅",               "#D4B46E"),
    (23, 32, "EMAILS 📧",                     "#D4B46E"),
    (33, 42, "DOCUMENTS 📄",                  "white"),
    (43, 52, "NAVIGATION WEB 🌐",             "#D4B46E"),
    (53, 62, "Vos données restent\nchez vous 🔒", "white"),
    (63, 75, "AMAH AGENT",                    "#D4B46E"),
]
add_keywords(
    os.path.join(DIR, "amah_v3_music.mp4"),
    os.path.join(DIR, "amah_v3_final.mp4"),
    kw_v3, is_vertical=False
)
print("  OK -> amah_v3_final.mp4")

# amah_v1_9x16 (vertical) — mots-clés
print("Mots-cles : amah_v1_9x16...")
kw_v1_9 = [
    (6,  13, "L'IA qui AGIT", "#D4B46E"),
    (20, 28, "3 SECONDES ⚡", "white"),
    (40, 48, "65 OUTILS", "#D4B46E"),
    (60, 68, "100% LOCAL 🔒", "white"),
    (78, 86, "AMAH AGENT 🚀", "#D4B46E"),
]
add_keywords(
    os.path.join(DIR, "amah_v1_9x16_music.mp4"),
    os.path.join(DIR, "amah_v1_9x16_final.mp4"),
    kw_v1_9, is_vertical=True
)
print("  OK -> amah_v1_9x16_final.mp4")


# ══════════════════════════════════════════════════════════════════════════════
print("\n=== FICHIERS FINAUX ===")
finals = [f for f in os.listdir(DIR) if f.endswith("_final.mp4")]
for f in sorted(finals):
    p = os.path.join(DIR, f)
    print(f"  {f:35} {os.path.getsize(p)//1024:5} Ko")
    os.startfile(p)
