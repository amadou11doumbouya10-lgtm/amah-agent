from config import TOOLS_DEFINITIONS
from tools.router_v03 import route_tools


TESTS = [
    # METEO
    "Il fait combien aujourd'hui ?",
    "Quel temps fait-il à Conakry ?",

    # FICHIERS
    "Montre-moi le contenu de contrat.pdf",
    "Peux-tu retrouver mon fichier CV ?",
    "Supprime ce fichier",
    "Modifie mon fichier config.py",

    # SYSTEME
    "Montre-moi les processus qui tournent actuellement",
    "Donne-moi les caractéristiques de mon ordinateur",

    # EMAIL
    "Envoie ce message par email",

    # MEMOIRE
    "Garde ça en mémoire",
    "Rappelle-moi ce que tu sais de mon projet",

    # STEAM
    "Ouvre Steam",
    "Cherche GTA sur Steam",
    "Installe ce jeu sur Steam",

    # VISION
    "Prends une capture de l'écran",
    "Regarde ce qu'il y a sur mon écran",

    # YOUTUBE
    "Va sur YouTube",
    "Cherche cette vidéo sur YouTube",

    # CODE
    "Écris une fonction Python",
    "Exécute mon script Python",

    # CHAT
    "Salut Amah",
    "Merci Amah",
    "Qu'est-ce que tu peux faire ?",

    # GENERAL
    "Calcule 250000 * 37",
    "Quelle heure est-il ?",
]


for text in TESTS:

    selected, intents = route_tools(
        text,
        TOOLS_DEFINITIONS,
        max_tools=12,
    )

    print("=" * 75)

    print("DEMANDE :")
    print(text)

    print()

    print("INTENTIONS :")
    print(intents)

    print()

    print("NOMBRE D'OUTILS :")
    print(len(selected))

    print()

    print("OUTILS :")

    for tool in selected:
        print(f"  - {tool['function']['name']}")

    print()