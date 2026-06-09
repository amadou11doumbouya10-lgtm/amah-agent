"""Génère des mockups réalistes de l'interface Amah Agent pour la vidéo."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

DIR  = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix\screens"
os.makedirs(DIR, exist_ok=True)

# Couleurs Amah Agent (identiques à gui.py)
BG_DARK  = (26,  26,  23)
BG_PANEL = (34,  34,  32)
BG_INPUT = (37,  37,  34)
GOLD     = (200, 169, 110)
GOLD_DIM = (122, 95,  56)
WHITE    = (232, 224, 208)
GREY     = (136, 136, 122)
TOOL_C   = (154, 122, 69)
RED_C    = (192, 57,  43)
DIM_C    = (74,  74,  66)
THINKING = (122, 95,  56)

W, H = 1400, 900


def font(size, bold=True):
    names = ["consola.ttf", "cour.ttf"] if not bold else ["consolab.ttf", "consola.ttf"]
    for n in names:
        try: return ImageFont.truetype(f"C:/Windows/Fonts/{n}", size)
        except: pass
    return ImageFont.load_default(size=size)


def draw_window(img, draw, title="The Amah — Agent Local"):
    """Dessine le cadre de fenêtre Windows avec barre de titre."""
    # Barre titre
    draw.rectangle([0, 0, W, 34], fill=(20, 20, 18))
    draw.text((16, 8), title, font=font(14, False), fill=GREY)
    # Boutons fenêtre
    for cx, col in [(W-50, (192,57,43)), (W-90, (241,196,15)), (W-130, (46,204,113))]:
        draw.ellipse([cx-8, 11, cx+8, 27], fill=col)


def draw_header(draw, tools_count=65):
    """En-tête THE AMAH."""
    draw.rectangle([0, 34, W, 100], fill=BG_PANEL)
    # Boutons
    for label, x in [("Copier", W-240), ("Reinitialiser", W-130)]:
        draw.rounded_rectangle([x-5, 46, x+len(label)*8+5, 86], radius=6, fill=(42, 42, 39))
        draw.text((x, 54), label, font=font(13, False), fill=GREY)
    # Titre centré
    t1 = "THE AMAH - AGENT LOCAL"
    draw.text((W//2 - 130, 44), t1, font=font(18), fill=GOLD)
    t2 = f"Groq  Llama 3.3  {tools_count} outils  Windows 11"
    draw.text((W//2 - 115, 72), t2, font=font(11, False), fill=GREY)
    # Séparateur
    draw.rectangle([0, 100, W, 101], fill=GOLD_DIM)


def draw_statusbar(draw, status="Pret"):
    """Barre de statut en bas."""
    draw.rectangle([0, H-36, W, H], fill=BG_PANEL)
    draw.text((14, H-24), status, font=font(11, False), fill=GREY)
    hint = "Shift+Entree = retour a la ligne  |  Ctrl+R = reinitialiser"
    draw.text((W-500, H-24), hint, font=font(10, False), fill=(58, 58, 50))


def draw_input_bar(draw, text=""):
    """Zone de saisie."""
    draw.rectangle([0, H-100, W, H-36], fill=BG_INPUT)
    draw.text((14, H-88), "Toi", font=font(13, False), fill=GREY)
    draw.text((48, H-88), ">", font=font(15), fill=GOLD_DIM)
    if text:
        draw.text((72, H-88), text, font=font(14, False), fill=WHITE)
    # Bouton envoyer
    draw.rounded_rectangle([W-110, H-96, W-14, H-46], radius=6, fill=GOLD_DIM)
    draw.text((W-88, H-82), "Envoyer", font=font(13), fill=BG_DARK)


def msg(draw, x, y, who, label, text, ts="10:32", tool=None):
    """Affiche un message dans le chat."""
    # Timestamp
    draw.text((x, y), f"[{ts}]", font=font(11, False), fill=DIM_C)
    # Label
    color = GOLD if who == "amah" else GREY
    lbl   = "Amah > " if who == "amah" else "Toi  > "
    draw.text((x+60, y), lbl, font=font(14), fill=color)
    # Texte principal
    draw.text((x+60 + draw.textlength(lbl, font=font(14)), y), label if label else "", font=font(14), fill=color)
    # Corps du message
    y2 = y + 28
    for line in text.split("\n"):
        draw.text((x+60, y2), line, font=font(13, False), fill=WHITE)
        y2 += 22
    if tool:
        draw.text((x+80, y2+4), f"  [ outil : {tool} ]", font=font(12, False), fill=TOOL_C)
        y2 += 24
    return y2 + 20


def separator(draw, y):
    draw.text((60, y), "  " + "-"*80, font=font(10, False), fill=DIM_C)
    return y + 18


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — Accueil / Premier message
# ══════════════════════════════════════════════════════════════════════════════
def screen_accueil():
    img  = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_window(img, draw)
    draw_header(draw)
    y = 120

    # Message de bienvenue
    y = msg(draw, 16, y, "amah", "",
        "Tu m'as trouvee. Qu'est-ce que tu veux faire ?", "10:30")
    draw.text((76, y), "  'outils' pour voir les outils · 'reset' pour reinitialiser", font=font(12, False), fill=GOLD_DIM)
    y += 40
    y = separator(draw, y)

    # Première demande utilisateur
    y = msg(draw, 16, y, "user", "Toi  > ", "organise mon bureau automatiquement", "10:31")
    y = separator(draw, y)

    # Réponse Amah avec outil
    y = msg(draw, 16, y, "amah", "",
        "J'organise votre bureau maintenant...\n"
        "Dossiers crees : Images/ Videos/ Documents/ Archives/\n"
        "47 fichiers deplaces — Bureau classe avec succes.", "10:31",
        tool="organisation dossier")
    y = separator(draw, y)

    draw_statusbar(draw, "Pret")
    draw_input_bar(draw)
    img.save(os.path.join(DIR, "screen1_accueil.png"))
    print("  screen1_accueil.png")


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — Email + recherche web
# ══════════════════════════════════════════════════════════════════════════════
def screen_email():
    img  = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_window(img, draw)
    draw_header(draw)
    y = 120

    y = msg(draw, 16, y, "user", "Toi  > ",
        "lis mes 3 derniers emails", "10:45")
    y = separator(draw, y)

    y = msg(draw, 16, y, "amah", "",
        "Voici vos 3 derniers emails :\n\n"
        "  1.  Google  |  Alerte de securite  |  Hier 23:53\n"
        "      Mot de passe d'application cree pour Amah-agent...\n\n"
        "  2.  LinkedIn  |  10 nouvelles connexions cette semaine\n"
        "      Vous avez 10 nouvelles invitations en attente...\n\n"
        "  3.  No-reply  |  Votre commande a ete expediee\n"
        "      Suivi : FR123456789 — Livraison prevue demain", "10:45",
        tool="lecture emails")
    y = separator(draw, y)

    y = msg(draw, 16, y, "user", "Toi  > ",
        "cherche les dernières actualites sur l'IA en 2025", "10:46")
    y = separator(draw, y)

    draw_statusbar(draw, "Outil : recherche web...")
    draw_input_bar(draw)
    img.save(os.path.join(DIR, "screen2_email.png"))
    print("  screen2_email.png")


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — Création de document
# ══════════════════════════════════════════════════════════════════════════════
def screen_document():
    img  = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_window(img, draw)
    draw_header(draw)
    y = 120

    y = msg(draw, 16, y, "user", "Toi  > ",
        "cree un rapport Word sur notre strategie commerciale Amah Agent", "11:02")
    y = separator(draw, y)

    y = msg(draw, 16, y, "amah", "",
        "Rapport Word genere avec succes !\n\n"
        "  Fichier  : Strategie_Commerciale_Amah.docx\n"
        "  Chemin   : C:/Users/.../Documents/\n"
        "  Taille   : 24.3 Ko\n"
        "  Contenu  : Introduction · Analyse marche · Cibles ·\n"
        "             Modele commercial · Roadmap · Conclusion", "11:02",
        tool="creation Word")
    y = separator(draw, y)

    y = msg(draw, 16, y, "user", "Toi  > ",
        "donne moi la meteo de paris pour demain", "11:03")
    y = separator(draw, y)

    y = msg(draw, 16, y, "amah", "",
        "Meteo Paris — Demain :\n"
        "  Temperatures : 18°C / 24°C\n"
        "  Ciel : Partiellement nuageux\n"
        "  Vent : 15 km/h SO | Humidite : 62%", "11:03",
        tool="meteo wttr.in")

    draw_statusbar(draw, "Pret — 65 outils disponibles")
    draw_input_bar(draw)
    img.save(os.path.join(DIR, "screen3_document.png"))
    print("  screen3_document.png")


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — Navigateur + mémoire
# ══════════════════════════════════════════════════════════════════════════════
def screen_navigateur():
    img  = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_window(img, draw)
    draw_header(draw)
    y = 120

    y = msg(draw, 16, y, "user", "Toi  > ",
        "ouvre linkedin et dis moi ce qu'il y a sur la page", "11:20")
    y = separator(draw, y)

    y = msg(draw, 16, y, "amah", "",
        "J'ai ouvert LinkedIn dans Chrome.\n"
        "Contenu de la page :\n"
        "  · 3 nouvelles connexions en attente\n"
        "  · 1 message non lu de Jean Dupont\n"
        "  · Votre post a obtenu 47 vues ce matin\n"
        "  · 2 offres d'emploi recommandees pour vous", "11:20",
        tool="navigation web · lecture page")
    y = separator(draw, y)

    y = msg(draw, 16, y, "user", "Toi  > ",
        "memorise que mon client principal s'appelle Jean Dupont", "11:21")
    y = separator(draw, y)

    y = msg(draw, 16, y, "amah", "",
        "Memorise dans la categorie 'client' :\n"
        "  Mon client principal s'appelle Jean Dupont\n"
        "Je m'en souviendrai lors de nos prochaines sessions.", "11:21",
        tool="memorisation")

    draw_statusbar(draw, "Pret")
    draw_input_bar(draw)
    img.save(os.path.join(DIR, "screen4_navigateur.png"))
    print("  screen4_navigateur.png")


screen_accueil()
screen_email()
screen_document()
screen_navigateur()
print("\n4 screenshots generes dans voix/screens/")
