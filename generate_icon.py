"""
Icône Amah — A propre via triangle plein + découpe + barre
Rendu 2048px → downsample 512px (anti-aliasing parfait)
"""
from PIL import Image, ImageDraw
import os, math

S    = 2048
OUT  = 512
DARK = (20, 18, 12, 255)
GOLD = (210, 175, 108, 255)


def rounded_mask(size, radius_pct):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    r = int(size * radius_pct)
    d.rounded_rectangle([0, 0, size-1, size-1], radius=r, fill=255)
    return m


def draw_A(draw, cx, top_y, bot_y, half_w, sw, gold, bg):
    H  = bot_y - top_y
    L  = math.sqrt(half_w**2 + H**2)

    # ── 1. Triangle extérieur plein (or) ──────────────────────
    draw.polygon([(cx, top_y), (cx - half_w, bot_y), (cx + half_w, bot_y)],
                 fill=gold)

    # ── 2. Découpe intérieure (fond) — même forme, décalée vers l'intérieur ──
    # L'apex intérieur est sw (perpendiculaire) plus bas que l'apex extérieur
    inner_apex_y   = top_y + sw * L / half_w
    H_inner        = bot_y - inner_apex_y
    inner_half_w   = half_w * H_inner / H

    draw.polygon([
        (cx,                  inner_apex_y),
        (cx - inner_half_w,   bot_y),
        (cx + inner_half_w,   bot_y),
    ], fill=bg)

    # ── 3. Barre horizontale (or) ─────────────────────────────
    bar_pct = 0.525          # position verticale (0=haut, 1=bas)
    bar_y   = top_y + H * bar_pct
    bar_h   = sw * 0.80

    # Largeur de la barre = largeur du triangle extérieur à cette hauteur
    outer_x = half_w * bar_pct
    bar_l   = cx - outer_x + sw * 0.08
    bar_r   = cx + outer_x - sw * 0.08

    draw.rectangle([bar_l, bar_y - bar_h / 2,
                    bar_r, bar_y + bar_h / 2], fill=gold)


def make(border=False):
    img  = Image.new("RGBA", (S, S), DARK)
    draw = ImageDraw.Draw(img)

    if border:
        pad = int(S * 0.042)
        lw  = int(S * 0.028)
        r   = int(S * 0.17)
        draw.rounded_rectangle([pad, pad, S-pad-1, S-pad-1],
                                radius=r, outline=GOLD[:3], width=lw)

    cx    = S // 2
    top_y = int(S * 0.155)
    bot_y = int(S * 0.845)
    H     = bot_y - top_y
    draw_A(draw, cx, top_y, bot_y,
           half_w = H * 0.47,
           sw     = H * 0.128,
           gold   = GOLD[:3],
           bg     = DARK[:3])

    # Appliquer les coins arrondis
    mask = rounded_mask(S, 0.185)
    out  = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(img, mask=mask)
    return out.resize((OUT, OUT), Image.LANCZOS)


def main():
    base = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent"

    v1 = make(border=False)
    v2 = make(border=True)

    p1 = os.path.join(base, "amah_final_v1.png")
    p2 = os.path.join(base, "amah_final_v2_border.png")

    v1.save(p1, "PNG")
    v2.save(p2, "PNG")

    print("OK  v1 — Sans cadre")
    print("OK  v2 — Avec cadre dore")

    os.startfile(p1)
    os.startfile(p2)


if __name__ == "__main__":
    main()
