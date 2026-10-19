"""
Adaptateur d'outils pour Gemini Live (mode vocal temps reel).

Le mode Live n'expose qu'un sous-ensemble "vocal-friendly" des outils Amah :
actions courtes, sans gros volumes de texte en sortie, utiles dans une
conversation orale (meteo, memoire, recherche, navigateur par texte visible,
hardware, musique...). Les outils de gestion de fichiers/code/jeux/plans
multi-etapes restent reserves a l'interface texte (gui.py / agent.py).

La conversion reutilise directement TOOLS_DEFINITIONS (config.py) : le champ
"parameters" (JSON Schema avec types en minuscules) est accepte tel quel par
google.genai.types.FunctionDeclaration via parameters_json_schema.
"""
from pathlib import Path

from google.genai import types

from config import TOOLS_DEFINITIONS

# ── Sous-ensemble d'outils disponibles en mode Live ─────────────────────────
GEMINI_TOOL_NAMES = {
    # Utilitaires
    "calculate", "get_datetime", "add_days", "generate_password", "convert_units",
    # Meteo / traduction
    "get_weather_simple", "get_weather", "translate", "detect_language",
    # Materiel
    "set_volume", "mute_audio", "set_brightness", "get_brightness", "wifi_toggle",
    # Memoire
    "save_memory", "get_memories", "delete_memory",
    # Recherche
    "web_search", "read_webpage",
    # Email
    "read_emails", "send_email",
    # Documents
    "create_pdf", "create_word",
    # Musique / video
    "play_music", "open_youtube",
    # Rappels / notifications
    "set_reminder", "send_notification",
    # Vision
    "analyze_screen", "analyze_webcam",
    # Navigateur (variantes sans selecteur CSS)
    "open_browser", "get_page_text", "click_text", "type_in_field",
}


def get_function_declarations():
    """Convertit le sous-ensemble Live de TOOLS_DEFINITIONS en FunctionDeclaration Gemini."""
    decls = []
    for tool in TOOLS_DEFINITIONS:
        fn = tool["function"]
        if fn["name"] not in GEMINI_TOOL_NAMES:
            continue
        decls.append(types.FunctionDeclaration(
            name=fn["name"],
            description=fn["description"],
            parameters_json_schema=fn["parameters"],
        ))
    return decls


def get_tools(extra=None):
    """Retourne la liste tools=[...] prete pour LiveConnectConfig. extra :
    déclarations au format OpenAI d'outils propres à l'interface (champ de texte…)."""
    decls = get_function_declarations()
    for tool in extra or []:
        fn = tool["function"]
        decls.append(types.FunctionDeclaration(name=fn["name"], description=fn["description"],
                                               parameters_json_schema=fn["parameters"]))
    return [types.Tool(function_declarations=decls)]


# ── Instruction systeme (condensee pour le mode audio temps reel) ───────────
_HOME      = str(Path.home()).replace("\\", "/")
_DESKTOP   = str(Path.home() / "Desktop").replace("\\", "/")
_DOCUMENTS = str(Path.home() / "Documents").replace("\\", "/")
_DOWNLOADS = str(Path.home() / "Downloads").replace("\\", "/")

GEMINI_SYSTEM_INSTRUCTION = """Tu es Amah, assistante IA vocale en temps reel, sur PC Windows.
Tu reponds en francais, a voix haute, de maniere naturelle, chaleureuse et concise (1-3 phrases courtes) -- comme dans une vraie conversation orale, jamais de listes a puces ni de blocs de code.

Identite : ton createur est Amadou Doumbouya. Stack reelle : Python, Groq/Gemini, Playwright, SQLite. Ne mentionne jamais TensorFlow/PyTorch/CNN/RNN comme faisant partie de ton architecture.

PC : Bureau={desktop} | Documents={documents} | Downloads={downloads}

Tu disposes d'outils pour agir reellement sur le PC (navigateur, email, meteo, musique, memoire, materiel...). Appelle-les directement quand l'utilisateur demande une action -- ne dis jamais que tu ne peux pas le faire.

Regles :
- Navigateur : utilise click_text(texte) et type_in_field(label, texte) -- jamais de selecteur CSS.
- Email : relis le contenu a l'utilisateur et demande confirmation orale avant d'envoyer avec send_email.
- Si une question porte sur un fait recent ou que tu n'es pas sure de connaitre, utilise web_search avant de repondre plutot que d'inventer.
- Garde toujours des reponses courtes et naturelles, adaptees a l'oral.
- Pour retrouver un projet, un site ou un compte de l'utilisateur, regarde d'abord son
  PROFIL ci-dessous, puis get_memories, avant toute recherche web.
- Si la voix est trop mal comprise, propose d'ouvrir le champ de texte (toggle_text_entry).

Mots que la reconnaissance vocale deforme chez cet utilisateur :
"jet top", "diptop", "git top", "lien dit op", et "YouTube" quand il parle de ses projets
ou de code = GitHub ; "chaine de test", "chant de texte",
"chat de test" = champ de texte ; "chambre de contact", "chat mail" = champ de contact,
champ e-mail ; "compte du top" = compte GitHub ; "a moi", "ama", "Hama" en debut de phrase = Amah (ton nom).
""".format(desktop=_DESKTOP, documents=_DOCUMENTS, downloads=_DOWNLOADS)


def live_instruction() -> str:
    """Instruction du mode Live au moment de la connexion : la base + la date
    du jour + le profil de l'utilisateur. Avant, Gemini ne connaissait ni ses
    projets, ni son GitHub, ni la date (test réel du 19/10/2026)."""
    from config import PROFILE_TEXT
    from tools.conversation import today_line
    text = GEMINI_SYSTEM_INSTRUCTION + "\n" + today_line()
    if PROFILE_TEXT:
        text += "\n\nPROFIL UTILISATEUR :\n" + PROFILE_TEXT
    return text
