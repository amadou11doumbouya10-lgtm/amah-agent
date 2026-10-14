"""
Amah Agent - Tool Router V0.3

Routeur local basé sur l'intention + action.

Objectifs :
- comprendre des formulations naturelles ;
- sélectionner le minimum d'outils nécessaire ;
- distinguer les actions d'une même catégorie ;
- ne faire aucun appel API ;
- rester indépendant de agent.py ;
- être rapide et déterministe.

IMPORTANT :
Cette version est expérimentale.
Elle n'est pas encore intégrée à agent.py.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


# ============================================================================
# 1. INTENTION -> OUTILS
# ============================================================================

INTENT_TOOLS = {
    # ------------------------------------------------------------------------
    # METEO
    # ------------------------------------------------------------------------

    "weather": {
        "get_weather",
        "get_weather_simple",
    },

    # ------------------------------------------------------------------------
    # FICHIERS
    # ------------------------------------------------------------------------

    "read_file": {
        "read_file",
    },

    "find_file": {
        "find_files",
    },

    "list_files": {
        "list_files",
    },

    "write_file": {
        "write_file",
    },

    "edit_file": {
        "read_file",
        "edit_file",
    },

    "delete_file": {
        "delete_file",
    },

    "move_file": {
        "move_file",
    },

    "create_folder": {
        "create_folder",
    },

    # ------------------------------------------------------------------------
    # NAVIGATEUR / WEB
    # ------------------------------------------------------------------------

    "youtube_open": {
        "open_youtube",
    },

    "youtube_search": {
        "open_youtube",
        "search_youtube",
    },

    "web_search": {
        "web_search",
        "read_webpage",
    },

    "browser_open": {
        "open_browser",
    },

    "browser_click": {
        "click_element",
        "click_text",
    },

    "browser_form": {
        "fill_form",
        "type_in_field",
    },

    # ------------------------------------------------------------------------
    # CODE
    # ------------------------------------------------------------------------

    "code_write": {
        "write_code",
    },

    "code_run": {
        "run_code",
    },

    "code_explain": {
        "explain_code",
    },

    "code_fix": {
        "read_file",
        "write_code",
        "run_code",
        "explain_code",
    },

    # ------------------------------------------------------------------------
    # SYSTEME
    # ------------------------------------------------------------------------

    "system_info": {
        "get_system_info",
    },

    "process_list": {
        "list_processes",
    },

    "network_info": {
        "get_network_info",
    },

    "wifi": {
        "wifi_toggle",
    },

    "volume": {
        "set_volume",
        "get_audio_level",
        "mute_audio",
    },

    "brightness": {
        "set_brightness",
        "get_brightness",
    },

    "command": {
        "run_command",
    },

    # ------------------------------------------------------------------------
    # EMAIL
    # ------------------------------------------------------------------------

    "send_email": {
        "send_email",
    },

    "email_read": {
        "read_emails",
    },

    "email_search": {
        "search_emails",
    },

    "email_draft": {
        "draft_email",
    },

    # ------------------------------------------------------------------------
    # MEMOIRE
    # ------------------------------------------------------------------------

    "memory_save": {
        "save_memory",
    },

    "memory_read": {
        "get_memories",
    },

    "memory_delete": {
        "delete_memory",
    },

    # ------------------------------------------------------------------------
    # STEAM / JEUX
    # ------------------------------------------------------------------------

    "steam_open": {
        "open_steam",
    },

    "steam_list": {
        "list_installed_steam_games",
    },

    "steam_launch": {
        "launch_game_steam",
    },

    "steam_search": {
        "search_game_on_steam",
    },

    "steam_install": {
        "install_game_steam",
    },

    "epic_open": {
        "open_epic_games",
    },

    # ------------------------------------------------------------------------
    # VISION
    # ------------------------------------------------------------------------

    "screenshot": {
        "take_screenshot",
        "screenshot_full",
    },

    "screen_analysis": {
        "take_screenshot",
        "analyze_screen",
    },

    "webcam": {
        "analyze_webcam",
    },

    "auto_mute": {
        "start_auto_mute",
        "stop_auto_mute",
    },

    # ------------------------------------------------------------------------
    # GENERAL
    # ------------------------------------------------------------------------

    "calculate": {
        "calculate",
    },

    "datetime": {
        "get_datetime",
    },

    "translate": {
        "translate",
        "detect_language",
    },
}


# ============================================================================
# 2. EXPRESSIONS DE DETECTION
# ============================================================================
#
# Deux types de patterns :
#
#   Texte normal :
#       "ouvre steam"
#
#   Expression régulière :
#       "re:cherche .+ sur steam"
#
# Les regex sont appliquées sur le texte NORMALISÉ.
# Elles doivent donc être écrites sans accents si nécessaire.
# ============================================================================

INTENT_PATTERNS = {

    # ------------------------------------------------------------------------
    # METEO
    # ------------------------------------------------------------------------

    "weather": [
        "meteo",
        "quel temps",
        "temps fait il",
        "il fait combien",
        "il fait combien aujourd",
        "temperature aujourd",
        "temperature actuelle",
        "temperature dehors",
        "fait il chaud",
        "fait il froid",
        "est ce qu il pleut",
        "va t il pleuvoir",
        "pleut il",
        "quelle temperature",
        "quel est le temps",
    ],

    # ------------------------------------------------------------------------
    # FICHIERS
    # ------------------------------------------------------------------------

    "read_file": [
        "lis le fichier",
        "lire le fichier",
        "ouvre le fichier",
        "ouvrir le fichier",
        "montre moi le contenu de",
        "montre le contenu de",
        "affiche le contenu de",
        "montre moi ce qu il y a dans",
        "regarde le contenu de",
    ],

    "find_file": [
        "cherche le fichier",
        "chercher le fichier",
        "trouve le fichier",
        "trouver le fichier",
        "retrouve mon fichier",
        "retrouver mon fichier",
        "peux tu retrouver mon fichier",
        "ou est mon fichier",
    ],

    "list_files": [
        "liste les fichiers",
        "liste les dossiers",
        "affiche les fichiers",
        "affiche les dossiers",
        "montre les fichiers",
        "montre les dossiers",
    ],

    "write_file": [
        "ecris dans le fichier",
        "ecrire dans le fichier",
        "écris dans le fichier",
        "écrire dans le fichier",
        "crée un fichier",
        "creer un fichier",
        "créer un fichier",
    ],

    "edit_file": [
        "modifie le fichier",
        "modifier le fichier",
        "modifie mon fichier",
        "modifier mon fichier",
        "edite le fichier",
        "édite le fichier",
        "corrige le fichier",
        "corriger le fichier",
    ],

    "delete_file": [
        "supprime le fichier",
        "supprimer le fichier",
        "efface le fichier",
        "effacer le fichier",
        "supprime ce fichier",
        "supprimer ce fichier",
    ],

    "move_file": [
        "deplace le fichier",
        "déplace le fichier",
        "déplacer le fichier",
        "deplacer le fichier",
    ],

    "create_folder": [
        "crée un dossier",
        "cree un dossier",
        "créer un dossier",
        "creer un dossier",
    ],

    # ------------------------------------------------------------------------
    # YOUTUBE
    # ------------------------------------------------------------------------

    "youtube_open": [
        "ouvre youtube",
        "ouvrir youtube",
        "va sur youtube",
        "aller sur youtube",
    ],

    "youtube_search": [
        "cherche sur youtube",
        "chercher sur youtube",
        "recherche sur youtube",
        "rechercher sur youtube",
        "cherche cette video sur youtube",
        "cherche cette vidéo sur youtube",
        "trouve une video sur youtube",
        "trouve une vidéo sur youtube",

        # Formulations naturelles :
        "re:cherche .+ sur youtube",
        "re:chercher .+ sur youtube",
        "re:recherche .+ sur youtube",
        "re:trouve .+ sur youtube",
    ],

    # ------------------------------------------------------------------------
    # WEB
    # ------------------------------------------------------------------------

    "web_search": [
        "cherche sur internet",
        "chercher sur internet",
        "recherche sur internet",
        "chercher sur le web",
        "cherche sur le web",
        "recherche web",
    ],

    "browser_open": [
        "ouvre le site",
        "ouvrir le site",
        "ouvre cette page",
        "ouvrir cette page",
        "va sur le site",
    ],

    "browser_click": [
        "clique sur",
        "cliquer sur",
        "click sur",
    ],

    "browser_form": [
        "remplis le formulaire",
        "remplir le formulaire",
        "ecris dans le champ",
        "écris dans le champ",
        "remplis ce champ",
    ],

    # ------------------------------------------------------------------------
    # CODE
    # ------------------------------------------------------------------------

    "code_fix": [
        "corrige mon code",
        "corrige le code",
        "corrige ce code",
        "repare mon code",
        "répare mon code",
        "repare ce programme",
        "répare ce programme",
    ],

    "code_write": [
        "ecris du code",
        "écris du code",
        "ecris une fonction",
        "écris une fonction",
        "crée une fonction python",
        "cree une fonction python",
        "créer une fonction python",
        "creer une fonction python",
        "programme ceci",
        "programmer ceci",
        "developpe ceci",
        "développe ceci",

        # Formulations naturelles :
        "re:ecris .* fonction .* python",
        "re:écris .* fonction .* python",
    ],

    "code_run": [
        "execute mon script",
        "exécute mon script",
        "execute ce script",
        "exécute ce script",
        "lance mon script python",
        "execute mon code",
        "exécute mon code",
    ],

    "code_explain": [
        "explique mon code",
        "explique ce code",
        "explique cette fonction",
    ],

    # ------------------------------------------------------------------------
    # SYSTEME
    # ------------------------------------------------------------------------

    "process_list": [
        "affiche les processus",
        "liste les processus",
        "montre les processus",
        "processus windows",
        "process windows",
        "processus qui tournent",
        "processus en cours",
        "programmes qui tournent",
        "programmes en cours",
    ],

    "system_info": [
        "caracteristiques de mon ordinateur",
        "caractéristiques de mon ordinateur",
        "caracteristiques de mon pc",
        "caractéristiques de mon pc",
        "informations de mon ordinateur",
        "informations du pc",
        "infos de mon pc",
        "configuration de mon pc",
        "configuration de mon ordinateur",
    ],

    "network_info": [
        "informations reseau",
        "informations réseau",
        "informations de mon reseau",
        "informations de mon réseau",
        "infos reseau",
        "infos réseau",
        "reseau de mon pc",
        "réseau de mon pc",
        "configuration reseau",
        "configuration réseau",
    ],

    "wifi": [
        "active le wifi",
        "active wifi",
        "desactive le wifi",
        "désactive le wifi",
        "coupe le wifi",
    ],

    "volume": [
        "augmente le volume",
        "baisse le volume",
        "monte le son",
        "baisse le son",
        "coupe le son",
        "mets en muet",
        "mute",
    ],

    "brightness": [
        "augmente la luminosite",
        "augmente la luminosité",
        "baisse la luminosite",
        "baisse la luminosité",
        "luminosite",
        "luminosité",
    ],

    "command": [
        "execute cette commande",
        "exécute cette commande",
        "lance cette commande",
        "commande powershell",
        "powershell",
    ],

    # ------------------------------------------------------------------------
    # EMAIL
    # ------------------------------------------------------------------------

    "send_email": [
        "envoie un email",
        "envoyer un email",
        "envoie un mail",
        "envoyer un mail",
        "envoie ce message par email",
        "envoyer ce message par email",
        "envoie ce message par mail",
        "envoyer ce message par mail",
    ],

    "email_read": [
        "lis mes emails",
        "lire mes emails",
        "lis mes mails",
        "lire mes mails",
    ],

    "email_search": [
        "cherche dans mes emails",
        "chercher dans mes emails",
        "cherche dans mes mails",
        "recherche dans mes emails",
    ],

    "email_draft": [
        "prepare un email",
        "prépare un email",
        "redige un brouillon",
        "rédige un brouillon",
        "prepare un brouillon",
        "prépare un brouillon",
    ],

    # ------------------------------------------------------------------------
    # MEMOIRE
    # ------------------------------------------------------------------------

    "memory_save": [
        "souviens toi",
        "souviens-toi",
        "retiens que",
        "garde ca en memoire",
        "garde ça en mémoire",
        "n oublie pas",
        "n'oublie pas",
    ],

    "memory_read": [
        "de quoi te souviens tu",
        "de quoi tu te souviens",
        "rappelle moi ce que tu sais",
        "rappelle-moi ce que tu sais",
        "qu est ce que tu sais de mon projet",
        "ce que tu sais de mon projet",
    ],

    "memory_delete": [
        "oublie ca",
        "oublie ça",
        "oublie cela",
        "supprime ce souvenir",
    ],

    # ------------------------------------------------------------------------
    # STEAM
    # ------------------------------------------------------------------------

    "steam_open": [
        "ouvre steam",
        "ouvrir steam",
        "lance steam",
        "lancer steam",
        "va sur steam",
    ],

    "steam_list": [
        "jeux installes sur steam",
        "jeux installés sur steam",
        "liste mes jeux steam",
        "liste les jeux steam",
        "quels jeux sont installes sur steam",
        "quels jeux sont installés sur steam",
    ],

    "steam_launch": [
        "lance le jeu sur steam",
        "lancer le jeu sur steam",
        "lance ce jeu sur steam",
        "ouvre le jeu sur steam",
        "joue a ce jeu",
        "joue à ce jeu",

        # Exemple :
        # "Lance GTA sur Steam"
        "re:lance .+ sur steam",
        "re:lancer .+ sur steam",
        "re:ouvre .+ sur steam",
        "re:joue .+ sur steam",
    ],

    "steam_search": [
        "cherche sur steam",
        "chercher sur steam",
        "recherche sur steam",
        "cherche ce jeu sur steam",
        "trouve ce jeu sur steam",

        # Exemple :
        # "Cherche GTA sur Steam"
        # "Cherche Cyberpunk 2077 sur Steam"
        "re:cherche .+ sur steam",
        "re:chercher .+ sur steam",
        "re:recherche .+ sur steam",
        "re:trouve .+ sur steam",
    ],

    "steam_install": [
        "installe ce jeu sur steam",
        "installer ce jeu sur steam",
        "installe le jeu sur steam",
        "installer le jeu sur steam",
        "telecharge ce jeu sur steam",
        "télécharge ce jeu sur steam",

        # Exemple :
        # "Installe GTA sur Steam"
        "re:installe .+ sur steam",
        "re:installer .+ sur steam",
        "re:telecharge .+ sur steam",
        "re:télécharge .+ sur steam",
    ],

    "epic_open": [
        "ouvre epic games",
        "ouvrir epic games",
        "lance epic games",
        "lancer epic games",
    ],

    # ------------------------------------------------------------------------
    # VISION
    # ------------------------------------------------------------------------

    "screenshot": [
        "capture de mon ecran",
        "capture de mon écran",
        "capture d ecran",
        "capture d'écran",
        "capture ecran",
        "capture écran",
        "screenshot",
        "fais une capture",
        "fait une capture",
        "prends une capture",
        "prend une capture",
    ],

    "screen_analysis": [
        "analyse mon ecran",
        "analyse mon écran",
        "analyse l ecran",
        "analyse l'écran",
        "regarde ce qu il y a sur mon ecran",
        "regarde ce qu il y a sur mon écran",
        "qu est ce qu il y a sur mon ecran",
        "qu est ce qu il y a sur mon écran",
        "regarde mon ecran",
        "regarde mon écran",
    ],

    "webcam": [
        "analyse ma webcam",
        "regarde avec la webcam",
        "ouvre la webcam",
        "utilise la webcam",
    ],

    "auto_mute": [
        "auto mute",
        "mute automatique",
        "coupe le micro automatiquement",
    ],

    # ------------------------------------------------------------------------
    # GENERAL
    # ------------------------------------------------------------------------

    "calculate": [
        "calcule",
        "calcul",
        "combien fait",
    ],

    "datetime": [
        "quelle heure",
        "quelle date",
        "date d aujourd hui",
        "heure actuelle",
    ],

    "translate": [
        "traduis",
        "traduire",
        "traduction",
    ],
}


# ============================================================================
# 3. NORMALISATION
# ============================================================================

def _normalize(text: str) -> str:
    """
    Normalise le texte utilisateur.

    Exemple :
        "Météo à Conakry !"
    devient :
        "meteo a conakry"
    """

    text = str(text).lower().strip()

    # Séparer les accents.
    text = unicodedata.normalize("NFD", text)

    # Supprimer les accents.
    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )

    # Apostrophes -> espace.
    text = text.replace("'", " ")
    text = text.replace("’", " ")

    # Ponctuation -> espace.
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Espaces multiples -> espace unique.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================================
# 4. NOM D'OUTIL
# ============================================================================

def _tool_name(tool: dict[str, Any]) -> str:
    """
    Récupère le nom d'un outil dans le format OpenAI/Groq.
    """

    try:
        return tool["function"]["name"]

    except (KeyError, TypeError):
        return ""


# ============================================================================
# 5. DETECTION DES INTENTIONS
# ============================================================================

def detect_intents(user_text: str) -> list[str]:
    """
    Détecte les intentions utilisateur.

    Les patterns normaux sont recherchés comme des sous-chaînes.

    Les patterns "re:" sont traités comme regex SUR LE TEXTE NORMALISÉ.
    """

    text = _normalize(user_text)

    scores: dict[str, int] = {}

    for intent, patterns in INTENT_PATTERNS.items():

        score = 0

        for pattern in patterns:

            # ------------------------------------------------------------
            # REGEX
            # ------------------------------------------------------------

            if pattern.startswith("re:"):

                regex = pattern[3:].strip()

                try:
                    if re.search(regex, text):
                        score += 1

                except re.error:
                    # Une regex invalide ne doit jamais casser le routeur.
                    continue

            # ------------------------------------------------------------
            # TEXTE NORMAL
            # ------------------------------------------------------------

            else:

                normalized_pattern = _normalize(pattern)

                if normalized_pattern in text:
                    score += 1

        if score > 0:
            scores[intent] = score

    # Les intentions avec le score le plus élevé sont prioritaires.
    return [
        intent
        for intent, _ in sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


# ============================================================================
# 6. CONVERSATION SIMPLE
# ============================================================================

CHAT_PATTERNS = [
    r"^bonjour\b",
    r"^salut\b",
    r"^bonsoir\b",
    r"^hello\b",
    r"^hey\b",
    r"comment vas tu",
    r"comment tu vas",
    r"ca va",
    r"merci\b",
    r"merci beaucoup",
    r"qu est ce que tu peux faire",
    r"que peux tu faire",
]


def is_simple_chat(user_text: str) -> bool:
    """
    Détermine si la demande est une conversation normale
    ne nécessitant aucun outil.
    """

    text = _normalize(user_text)

    return any(
        re.search(pattern, text)
        for pattern in CHAT_PATTERNS
    )


# ============================================================================
# 7. ROUTEUR PRINCIPAL
# ============================================================================

def route_tools(
    user_text: str,
    tools_definitions: list[dict[str, Any]],
    max_tools: int = 12,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Sélectionne les outils nécessaires à une demande.

    Retour :
        (
            liste des définitions d'outils,
            liste des intentions détectées
        )

    Important :
        aucune requête réseau/API n'est effectuée ici.
    """

    # ------------------------------------------------------------------------
    # 1. Conversation simple
    # ------------------------------------------------------------------------

    if is_simple_chat(user_text):
        return [], []


    # ------------------------------------------------------------------------
    # 2. Détection des intentions
    # ------------------------------------------------------------------------

    intents = detect_intents(user_text)

    if not intents:
        return [], []


    # ------------------------------------------------------------------------
    # 3. Sélection des outils
    # ------------------------------------------------------------------------

    selected: list[dict[str, Any]] = []

    selected_names: set[str] = set()

    for intent in intents:

        allowed_tools = INTENT_TOOLS.get(intent, set())

        for tool in tools_definitions:

            name = _tool_name(tool)

            if not name:
                continue

            if name in selected_names:
                continue

            if name not in allowed_tools:
                continue

            selected.append(tool)
            selected_names.add(name)

            # Limite de sécurité/performance.
            if len(selected) >= max_tools:
                return selected, intents

    return selected, intents