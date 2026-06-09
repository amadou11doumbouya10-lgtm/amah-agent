"""Ajout de texte sur toutes les vidéos avec drawtext FFmpeg."""
import subprocess, os

FFMPEG = r"C:\Users\Smarte technologui\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
DIR    = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
FONT   = r"C\:/Windows/Fonts/arialbd.ttf"
FONTL  = r"C\:/Windows/Fonts/arial.ttf"


def run(src, dst, filters):
    vf = ",".join(filters)
    r  = subprocess.run([FFMPEG, "-y", "-i", src, "-vf", vf, "-c:a", "copy", dst], capture_output=True)
    ok = os.path.exists(dst) and os.path.getsize(dst) > 0
    print(f"  {'OK' if ok else 'ERR'} -> {os.path.basename(dst)} ({os.path.getsize(dst)//1024 if ok else 0} Ko)")
    if ok: os.startfile(dst)
    return ok


def subtitle_filter(entries, font=FONT, fs=68, color="white", bcolor="black", bw=3, mv=100):
    """Construit les filtres drawtext pour des sous-titres temporisés."""
    filters = []
    for start, end, text in entries:
        # Remplace les retours à la ligne par un espace (drawtext ne supporte pas \n facilement)
        lines = text.split("\n")
        for li, line in enumerate(lines):
            y_off = mv + li * (fs + 8)
            safe  = line.replace("'", "").replace(":", "\\:").replace("%", "%%")
            fade  = min(0.3, (end-start)/4)
            alpha = f"if(lt(t-{start},{fade}),(t-{start})/{fade},if(lt(t,{end}-{fade}),1,({end}-t)/{fade}))"
            filters.append(
                f"drawtext=fontfile='{font}':text='{safe}':"
                f"fontsize={fs}:fontcolor={color}:bordercolor={bcolor}:borderw={bw}:"
                f"x=(w-text_w)/2:y=h-{y_off}:"
                f"alpha='{alpha}':enable='between(t\\,{start}\\,{end})'"
            )
    return filters


def keyword_filter(entries, font=FONT, fs=72, mv=160):
    """Mots-clés d'accroche animés."""
    filters = []
    for start, end, text, color in entries:
        safe  = text.replace("'","").replace(":", "\\:").replace("%","%%")
        fade  = min(0.4, (end-start)/3)
        alpha = f"if(lt(t-{start},{fade}),(t-{start})/{fade},if(lt(t,{end}-{fade}),1,({end}-t)/{fade}))"
        filters.append(
            f"drawtext=fontfile='{font}':text='{safe}':"
            f"fontsize={fs}:fontcolor={color}:bordercolor=black:borderw=4:"
            f"x=(w-text_w)/2:y=h-{mv}:"
            f"alpha='{alpha}':enable='between(t\\,{start}\\,{end})'"
        )
    return filters


# ══════════════════════════════════════════════════════════════════════════════
# OPTION 1 — SOUS-TITRES (concept3, concept4, amah_v3_9x16)
# ══════════════════════════════════════════════════════════════════════════════

print("=== SOUS-TITRES ===")

# Concept 3 TikTok Hook
print("concept3...")
run(
    os.path.join(DIR, "concept3_music.mp4"),
    os.path.join(DIR, "concept3_final.mp4"),
    subtitle_filter([
        (0,   3,  "Regardez ca."),
        (3,   6,  "Mon IA en 3 secondes."),
        (6.5, 11, "Organise mon bureau."),
        (11,  14, "Tout classe. En 3s."),
        (14.5,18, "Lis mes emails."),
        (18,  21, "Elle les lit."),
        (21.5,25, "Je veux un rapport Word."),
        (25,  28, "Il est pret."),
        (28.5,33, "65 choses qu'Amah fait."),
        (33,  37, "Automatiquement."),
        (37.5,42, "Sur votre PC."),
        (42.5,46, "Donnees chez vous."),
        (47,  50, "contact.amah.officiel@gmail.com"),
    ], fs=62, mv=120)
)

# Concept 4 Avant/Après
print("concept4...")
run(
    os.path.join(DIR, "concept4_music.mp4"),
    os.path.join(DIR, "concept4_final.mp4"),
    subtitle_filter([
        (0,   4,  "Avant Amah."),
        (4.5, 9,  "2h pour classer mes fichiers."),
        (9.5, 14, "10 min pour un email."),
        (14.5,18, "1h pour un rapport."),
        (19,  23, "Avec Amah."),
        (23.5,28, "Fichiers classes. 3 secondes."),
        (28.5,33, "Email trouve. 5 secondes."),
        (33.5,38, "Rapport genere. 30 secondes."),
        (39,  43, "C'est ca la difference."),
        (44,  49, "AMAH AGENT"),
        (49.5,54, "L'IA qui agit vraiment."),
        (55,  59, "contact.amah.officiel@gmail.com"),
    ], fs=62, mv=120)
)

# amah_v3_9x16
print("amah_v3_9x16...")
run(
    os.path.join(DIR, "amah_v3_9x16_music.mp4"),
    os.path.join(DIR, "amah_v3_9x16_final.mp4"),
    subtitle_filter([
        (0,   7,  "Un assistant IA sur votre PC."),
        (7,  16,  "Organise mon bureau."),
        (16,  24, "47 fichiers classes en 3s."),
        (24,  34, "Lis mes emails."),
        (34,  44, "Resume immediat."),
        (44,  56, "Vos donnees restent chez vous."),
        (57,  64, "contact.amah.officiel@gmail.com"),
    ], fs=62, mv=120)
)


# ══════════════════════════════════════════════════════════════════════════════
# OPTION 2 — MOTS-CLÉS D'ACCROCHE (amah_v1, amah_v3, amah_v1_9x16)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== MOTS-CLES ===")

# amah_v1 16:9
print("amah_v1...")
run(
    os.path.join(DIR, "amah_v1_music.mp4"),
    os.path.join(DIR, "amah_v1_final.mp4"),
    keyword_filter([
        (8,  15, "L'IA qui AGIT vraiment",  "white"),
        (22, 30, "3 SECONDES",               "#D4B46E"),
        (40, 48, "65 OUTILS",                "#D4B46E"),
        (55, 63, "100% LOCAL",               "white"),
        (68, 76, "MEMOIRE PERSISTANTE",      "#D4B46E"),
        (82, 92, "AMAH AGENT",               "#D4B46E"),
    ], fs=68, mv=140)
)

# amah_v3 16:9 interface
print("amah_v3...")
run(
    os.path.join(DIR, "amah_v3_music.mp4"),
    os.path.join(DIR, "amah_v3_final.mp4"),
    keyword_filter([
        (5,  13, "Dites. Elle fait.",     "white"),
        (20, 29, "EMAILS",                "#D4B46E"),
        (30, 39, "DOCUMENTS",             "white"),
        (40, 50, "NAVIGATION WEB",        "#D4B46E"),
        (51, 60, "100% LOCAL",            "white"),
        (62, 75, "AMAH AGENT",            "#D4B46E"),
    ], fs=68, mv=140)
)

# amah_v1_9x16
print("amah_v1_9x16...")
run(
    os.path.join(DIR, "amah_v1_9x16_music.mp4"),
    os.path.join(DIR, "amah_v1_9x16_final.mp4"),
    keyword_filter([
        (6,  14, "L'IA qui AGIT",   "#D4B46E"),
        (22, 30, "3 SECONDES",      "white"),
        (42, 50, "65 OUTILS",       "#D4B46E"),
        (60, 68, "100% LOCAL",      "white"),
        (78, 88, "AMAH AGENT",      "#D4B46E"),
    ], fs=82, mv=160)
)

print("\nTERMINE - 6 videos finales creees !")
