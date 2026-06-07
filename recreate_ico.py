"""Crée amah.ico — recadre uniquement l'hexagone (sans le texte en dessous)."""
from PIL import Image
import os, struct, io

PNG = "amah_logo_hex.png"
ICO = "amah.ico"

img = Image.open(PNG).convert("RGBA")
W, H = img.size
print(f"PNG source : {W}x{H}")

# L'hexagone occupe environ le haut de l'image (avant le texte AMAH / AGENT)
# Dans un canvas 680x680, l'hexagone va de y≈30 à y≈360, centré
# On recadre avec un peu de marge autour de l'hexagone
margin = 20
crop_x1 = int(W * 0.28)   # ≈ 190px — bord gauche hexagone
crop_y1 = int(H * 0.04)   # ≈ 27px  — sommet hexagone
crop_x2 = int(W * 0.72)   # ≈ 490px — bord droit hexagone
crop_y2 = int(H * 0.50)   # ≈ 340px — base hexagone (avant le texte)

# On rend carré (prendre le max des deux dimensions)
cw = crop_x2 - crop_x1
ch = crop_y2 - crop_y1
side = max(cw, ch) + margin * 2
cx  = W // 2
cy  = (crop_y1 + crop_y2) // 2

x1 = max(0, cx - side // 2)
y1 = max(0, cy - side // 2)
x2 = min(W, x1 + side)
y2 = min(H, y1 + side)

hexagon = img.crop((x1, y1, x2, y2))
print(f"Zone recadree : ({x1},{y1}) -> ({x2},{y2}) = {hexagon.size}")

# Fond noir pour compléter si besoin
bg = Image.new("RGBA", (side, side), (8, 7, 5, 255))
offset_x = (side - hexagon.size[0]) // 2
offset_y = (side - hexagon.size[1]) // 2
bg.paste(hexagon, (offset_x, offset_y), hexagon)
hexagon = bg

# Aperçu avant de créer l'ico
hexagon.save("amah_ico_hex_crop.png")
print("Apercu crop sauvegarde")

# Création ICO multi-tailles
def make_ico(src_img, ico_path):
    sizes  = [256, 128, 64, 48, 32, 16]
    images = []
    for s in sizes:
        r   = src_img.resize((s, s), Image.LANCZOS)
        buf = io.BytesIO()
        r.save(buf, format="PNG")
        images.append((s, buf.getvalue()))

    n      = len(images)
    header = struct.pack("<HHH", 0, 1, n)
    dir_sz = n * 16
    offset = 6 + dir_sz
    directory  = b""
    image_data = b""
    for (s, data) in images:
        w = s if s < 256 else 0
        directory  += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(data), offset)
        image_data += data
        offset     += len(data)

    with open(ico_path, "wb") as f:
        f.write(header + directory + image_data)
    return os.path.getsize(ico_path)

size_bytes = make_ico(hexagon, ICO)
print(f"amah.ico : {size_bytes:,} octets ({size_bytes//1024} Ko) — hexagone seul")

# Aperçu final
check = Image.open(ICO)
final = hexagon.resize((256, 256), Image.LANCZOS)
final.convert("RGB").save("amah_ico_preview_final.png")
os.startfile("amah_ico_preview_final.png")
print("Apercu final ouvert !")
