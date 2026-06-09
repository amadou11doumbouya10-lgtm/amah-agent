"""Ajoute la musique de fond à toutes les vidéos (voix au premier plan)."""
import subprocess, os

FFMPEG = r"C:\Users\Smarte technologui\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
DIR    = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
MUSIC  = os.path.join(DIR, "musique_amah.wav")

# Toutes les vidéos à enrichir
VIDEOS = [
    ("amah_presentation.mp4",      "amah_v1_music.mp4"),
    ("amah_v3_interface.mp4",       "amah_v3_music.mp4"),
    ("amah_v1_9x16.mp4",           "amah_v1_9x16_music.mp4"),
    ("amah_v3_9x16.mp4",           "amah_v3_9x16_music.mp4"),
    ("concept3_tiktok_hook.mp4",   "concept3_music.mp4"),
    ("concept4_avant_apres.mp4",   "concept4_music.mp4"),
]

print("Ajout musique de fond sur toutes les videos...")
print(f"Volume musique : -22dB (voix domine largement)\n")

for src_name, dst_name in VIDEOS:
    src = os.path.join(DIR, src_name)
    dst = os.path.join(DIR, dst_name)
    if not os.path.exists(src):
        print(f"  SKIP {src_name} (introuvable)")
        continue
    print(f"  {src_name} -> {dst_name}")
    # Mix : voix 0dB + musique -22dB, coupé à la durée de la vidéo
    subprocess.run([
        FFMPEG, "-y",
        "-i", src,          # vidéo avec voix
        "-stream_loop", "-1", "-i", MUSIC,  # musique en boucle
        "-filter_complex",
        "[0:a]volume=1.0[voice];[1:a]volume=0.07[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        dst
    ], capture_output=True)
    size = os.path.getsize(dst) // 1024
    print(f"  OK — {size} Ko")

print("\nTous les fichiers avec musique sont prets !")
print("\nFICHIERS FINAUX (avec musique) :")
finals = [f for f in os.listdir(DIR) if f.endswith("_music.mp4")]
for f in sorted(finals):
    path = os.path.join(DIR, f)
    print(f"  {f:45} {os.path.getsize(path)//1024:5} Ko")
    os.startfile(path)
