"""Vérifie l'extraction du contenu principal des pages et la lecture à voix
haute (tools/page_text.py, tools/reader.py, tools/instant.py) — sans réseau,
sans son, sans appel API.

Lancer depuis la racine du projet :
    py -3.13 -m benchmarks.benchmark_page_text

Code de sortie 1 si une vérification échoue.
"""
import sys
import threading

from tools import instant, reader
from tools.page_text import extract_main_text

results = []


def check(label, condition):
    results.append(bool(condition))
    print(("OK    " if condition else "ECHEC ") + label)


# Paragraphes tous différents : l'extracteur retire les lignes répétées
_N = iter(range(1000))


def para():
    return " ".join(f"Conakry est la capitale de la Guinée, phrase {next(_N)} au bord de l'océan." for _ in range(6))


MENU = "<nav><ul>" + "".join(f"<li><a href='#'>Rubrique {i}</a></li>" for i in range(30)) + "</ul></nav>"
COOKIES = "<div class='cookie-banner'><p>Nous utilisons des cookies pour améliorer votre expérience de navigation sur ce site.</p></div>"

# 1. Le menu, le bandeau cookies et le pied de page ne passent plus avant l'article
page = (f"<html><head><title>Conakry | Site</title></head><body>{COOKIES}<header>Se connecter</header>{MENU}"
        f"<article><h1>Conakry</h1><p>{para()}</p><p>{para()}</p></article>"
        f"<footer><p>Mentions légales, plan du site, contact et autres liens du pied de page.</p></footer></body></html>")
r = extract_main_text(page)
check("article seul : ni menu, ni cookies, ni pied de page",
      "Rubrique" not in r["texte"] and "cookies" not in r["texte"] and "Mentions" not in r["texte"])
check("article en entier (2 paragraphes)", r["texte"].count("Conakry est la capitale") == 12)
check("titre de l'article (h1) en tête", r["titre"] == "Conakry" and r["texte"].startswith("Conakry"))

# 2. Wikipédia : la classe du <body> contient "menu" -> la page ne doit pas disparaître
wiki = (f"<html><body class='skin-vector vector-feature-main-menu-pinned-disabled'>{MENU}"
        f"<main id='content' class='mw-body'><h1>Conakry</h1>"
        f"<table class='infobox_v3'><tr><td>Pays Guinée Population Superficie Altitude</td></tr></table>"
        f"<div id='mw-content-text'><p>{para()}</p><p>{para()}</p></div></main></body></html>")
r = extract_main_text(wiki)
check("Wikipédia : article trouvé malgré 'menu' dans la classe du body", "Conakry est la capitale" in r["texte"])
check("Wikipédia : encadré (infobox) écarté", "Superficie" not in r["texte"])

# 3. Sans <article> ni <main> : le bloc le plus riche en paragraphes
divs = (f"<html><body>{MENU}<div class='colonne'><p>Lien court</p></div>"
        f"<div class='contenu-principal'><h2>Histoire</h2><p>{para()}</p><p>{para()}</p><p>{para()}</p></div>"
        f"<div class='related-articles'><p>{para()[:120]} (article lié)</p></div></body></html>")
r = extract_main_text(divs)
check("sans balise article : bloc principal trouvé",
      r["texte"].count("Conakry est la capitale") == 18 and "Lien court" not in r["texte"])
check("articles liés écartés", "article lié" not in r["texte"])

# 4. Page sans article (accueil) : tout le texte hors menus plutôt que rien
home = "<html><body>" + MENU + "".join(f"<div><a href='#'>Titre d'actualité numéro {i}</a></div>" for i in range(20)) + "</body></html>"
r = extract_main_text(home)
check("page d'accueil : les titres sont gardés", "numéro 19" in r["texte"] and "Rubrique" not in r["texte"])
check("HTML vide : pas d'erreur", extract_main_text("") == {"titre": "", "texte": ""})

# 5. Découpage pour la voix : rien de perdu, morceaux courts
long_text = ("Une phrase. " * 200) + "\n" + ("liste sans point " * 120)
chunks = reader._chunks(long_text)
check("découpage : morceaux de 600 caractères max", max(map(len, chunks)) <= 600)
check("découpage : aucun mot perdu", " ".join(chunks).split() == long_text.split())

# 6. "Arrête la lecture" : seulement pendant une lecture, sans appel IA
check("sans lecture en cours, 'stop' n'est pas intercepté", instant.stop_reading_reply("stop") is None)
done = threading.Event()
reader._thread = threading.Thread(target=done.wait, daemon=True)
reader._thread.start()
stops = ["arrête la lecture", "stop", "Amah tais-toi", "arrête de lire", "ça suffit"]
others = ["arrête le PC", "stop au bruit dans la rue", "arrête-toi à la boulangerie demain"]
check("pendant la lecture : 'arrête la lecture', 'stop', 'tais-toi'... reconnus",
      all(instant._STOP_READING.match(q) for q in stops))
check("pendant la lecture : 'arrête le PC'... pas pris pour un arrêt",
      not any(instant._STOP_READING.match(q) for q in others))
done.set()
reader._thread.join()
reader._thread = None

print(f"\n{sum(results)}/{len(results)} vérifications réussies")
sys.exit(0 if all(results) else 1)
