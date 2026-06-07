"""Convertit le SVG hexagone en PNG haute résolution puis en .ico pour Amah Agent."""
import os, subprocess
from pathlib import Path
from PIL import Image

SVG_PATH = r"C:\Users\Smarte technologui\Downloads\amah_agent_logo_v3_hex.svg"
PNG_PATH  = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\amah_logo_hex.png"
ICO_PATH  = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\amah.ico"
PROJ      = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent"

# ── Étape 1 : SVG → PNG via Playwright (rendu navigateur exact) ───────────────
print("Rendu SVG via Playwright...")

html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ margin: 0; padding: 0; background: #0a0a0a; display: flex;
         align-items: center; justify-content: center;
         width: 680px; height: 680px; }}
  svg {{ width: 680px; height: 680px; }}
</style>
</head>
<body>
{open(SVG_PATH, encoding='utf-8').read()}
</body>
</html>"""

html_path = os.path.join(PROJ, "_logo_render.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page    = browser.new_page(viewport={"width": 680, "height": 680})
    page.goto(f"file:///{html_path.replace(chr(92), '/')}")
    page.wait_for_timeout(500)
    page.screenshot(path=PNG_PATH, full_page=False)
    browser.close()

print(f"PNG cree : {PNG_PATH}")
os.remove(html_path)

# ── Étape 2 : PNG → .ico multi-taille ────────────────────────────────────────
print("Creation du .ico...")
img  = Image.open(PNG_PATH).convert("RGBA")
sizes = [16, 32, 48, 64, 128, 256]
icons = [img.resize((s, s), Image.LANCZOS) for s in sizes]
icons[0].save(ICO_PATH, format="ICO",
              sizes=[(s, s) for s in sizes],
              append_images=icons[1:])
print(f".ico cree : {ICO_PATH}")

# ── Aperçu ───────────────────────────────────────────────────────────────────
os.startfile(PNG_PATH)
print("Apercu ouvert !")
