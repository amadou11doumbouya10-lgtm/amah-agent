import os
from pathlib import Path

MODEL = "llama-3.3-70b-versatile"

_HOME      = str(Path.home()).replace("\\", "/")
_DESKTOP   = str(Path.home() / "Desktop").replace("\\", "/")
_DOCUMENTS = str(Path.home() / "Documents").replace("\\", "/")
_DOWNLOADS = str(Path.home() / "Downloads").replace("\\", "/")

# Le texte du prompt systeme vit dans system_prompt.txt (a la racine du projet)
# pour pouvoir etre relu/edite sans toucher au code -- seules les variables PC
# (chemins Bureau/Documents/Downloads) restent injectees ici via .format().
_PROMPT_PATH = Path(__file__).resolve().parent / "system_prompt.txt"
SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8").format(
    desktop=_DESKTOP, documents=_DOCUMENTS, downloads=_DOWNLOADS,
)

# ── Définitions compactes des outils (tokens optimisés) ─────────────────────
def _f(name, desc, props=None, required=None):
    params = {"type": "object", "properties": props or {}, "required": required or []}
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": params}}

def _s(desc): return {"type": "string",  "description": desc}
def _i(desc): return {"type": "integer", "description": desc}
def _n(desc): return {"type": "number",  "description": desc}
def _b(desc): return {"type": "boolean", "description": desc}
def _a(desc): return {"type": "array",   "items": {"type": "string"}, "description": desc}
def _aa(desc): return {"type": "array",  "items": {"type": "array"},  "description": desc}

TOOLS_DEFINITIONS = [
    # Fichiers
    _f("list_files",      "Liste un dossier",                   {"path": _s("chemin")}, ["path"]),
    _f("organize_folder", "Classe fichiers par type",           {"path": _s("chemin")}, ["path"]),
    _f("find_files",      "Cherche fichiers par nom",           {"path": _s("dossier"), "pattern": _s("motif")}, ["path","pattern"]),
    _f("move_file",       "Deplace ou renomme un fichier",      {"source": _s("source"), "destination": _s("dest")}, ["source","destination"]),
    _f("create_folder",   "Cree un dossier",                    {"path": _s("chemin")}, ["path"]),
    _f("read_file",       "Lit un fichier texte",               {"path": _s("chemin")}, ["path"]),
    _f("write_file",      "Ecrit/cree un fichier texte (html, py, js, css, txt, md). NE PAS utiliser sur .pdf ou .docx — utiliser create_pdf/create_word a la place.", {"path": _s("chemin"), "content": _s("contenu complet")}, ["path","content"]),
    _f("edit_file",       "Remplace un texte dans un fichier existant",        {"path": _s("chemin"), "old_text": _s("texte a remplacer"), "new_text": _s("nouveau texte")}, ["path","old_text","new_text"]),
    _f("edit_pdf",        "Modifie du texte dans un PDF existant en gardant la mise en page (logo, tableau, couleurs). Utiliser TOUJOURS pour modifier un .pdf", {"path": _s("chemin PDF"), "old_text": _s("texte a remplacer"), "new_text": _s("nouveau texte")}, ["path","old_text","new_text"]),
    _f("get_folder_info", "Stats taille/types d'un dossier",    {"path": _s("chemin")}, ["path"]),
    _f("delete_file",     "Supprime definitivement un fichier ou dossier", {"path": _s("chemin du fichier ou dossier")}, ["path"]),
    _f("summarize",       "Lit un fichier (pdf/docx/txt/code) pour en faire un résumé IA", {"path": _s("chemin du fichier a resumer")}, ["path"]),
    # Documents
    _f("create_word",     "Cree un fichier Word",               {"filename": _s("nom"), "title": _s("titre"), "content": _s("contenu"), "save_path": _s("dossier")}, ["filename","title","content"]),
    _f("create_txt",      "Cree un fichier TXT",                {"filename": _s("nom"), "content": _s("contenu"), "save_path": _s("dossier")}, ["filename","content"]),
    _f("create_pdf",      "Cree un fichier PDF",                {"filename": _s("nom"), "title": _s("titre"), "content": _s("contenu"), "save_path": _s("dossier")}, ["filename","title","content"]),
    _f("read_document",   "Lit Word/PDF/TXT",                   {"path": _s("chemin")}, ["path"]),
    # Recherche
    _f("web_search",      "Recherche DuckDuckGo",               {"query": _s("requete"), "num_results": _i("nb resultats")}, ["query"]),
    _f("read_webpage",    "Lit texte d'une page web",           {"url": _s("url")}, ["url"]),
    # Systeme
    _f("get_system_info", "RAM/CPU/disque/OS"),
    _f("open_file",       "Ouvre fichier ou dossier Windows",   {"path": _s("chemin")}, ["path"]),
    _f("run_command",     "Execute commande PowerShell",        {"command": _s("commande")}, ["command"]),
    _f("list_processes",  "Liste processus actifs par CPU",     {"top": _i("nb")}),
    _f("get_network_info","IP locale et connexion internet"),
    _f("kill_process",    "Termine un processus par nom ou PID (protege les processus systeme critiques)", {"name": _s("nom du processus ex: chrome.exe"), "pid": _i("PID du processus")}, []),
    # Memoire
    _f("save_memory",     "Memorise une info",                  {"content": _s("info"), "category": _s("categorie")}, ["content"]),
    _f("get_memories",    "Rappelle les infos memorisees",      {"category": _s("categorie")}),
    _f("delete_memory",   "Supprime une memoire",               {"memory_id": _i("id")}, ["memory_id"]),
    # Email
    _f("read_emails",     "Lit derniers emails Gmail",          {"n": _i("nb")}),
    _f("send_email",      "Envoie un email Gmail",              {"to": _s("destinataire"), "subject": _s("sujet"), "body": _s("corps")}, ["to","subject","body"]),
    _f("search_emails",   "Cherche emails Gmail",               {"query": _s("requete")}, ["query"]),
    _f("draft_email",     "Prepare un brouillon email sans envoyer (montre a l'utilisateur pour validation)", {"to": _s("destinataire"), "subject": _s("sujet"), "body": _s("corps")}, ["to","subject","body"]),
    # Navigateur
    _f("open_browser",    "Ouvre URL dans Chrome",              {"url": _s("url")}, ["url"]),
    _f("click_element",   "Clique element de la page",          {"selector": _s("selecteur CSS")}, ["selector"]),
    _f("fill_form",       "Remplit champ formulaire",           {"selector": _s("selecteur"), "value": _s("valeur")}, ["selector","value"]),
    _f("take_screenshot", "Capture ecran navigateur",           {"path": _s("chemin")}),
    _f("get_page_text",   "Lit texte de la page ouverte"),
    _f("click_text",      "Clique sur un element par son texte visible (bouton, lien...) -- pas de selecteur CSS requis", {"text": _s("texte visible de l'element a cliquer")}, ["text"]),
    _f("type_in_field",   "Ecrit du texte dans un champ par son label/placeholder -- pas de selecteur CSS requis", {"label": _s("label, placeholder ou nom du champ"), "text": _s("texte a saisir")}, ["label","text"]),
    # Voix
    _f("speak",           "Parle a voix haute",                 {"text": _s("texte"), "speed": _i("vitesse")}, ["text"]),
    _f("listen",          "Ecoute microphone",                  {"timeout": _i("secondes"), "language": _s("langue")}),
    _f("listen_continuous","Ecoute microphone X secondes",      {"duration": _i("secondes"), "language": _s("langue")}),
    # Notifications
    _f("send_notification","Notification Windows",              {"title": _s("titre"), "message": _s("message"), "duration": _i("duree")}, ["title","message"]),
    _f("set_reminder",    "Rappel dans X minutes",              {"message": _s("message"), "minutes": _i("minutes")}, ["message","minutes"]),
    # Excel
    _f("read_excel",      "Lit fichier Excel",                  {"path": _s("chemin")}, ["path"]),
    _f("create_excel",    "Cree fichier Excel",                 {"filename": _s("nom"), "headers": _a("colonnes"), "rows": _aa("lignes"), "save_path": _s("dossier")}, ["filename","headers","rows"]),
    _f("append_to_excel", "Ajoute lignes Excel",               {"path": _s("chemin"), "rows": _aa("lignes")}, ["path","rows"]),
    # Presse-papiers
    _f("read_clipboard",  "Lit le presse-papiers"),
    _f("write_clipboard", "Copie texte presse-papiers",         {"text": _s("texte")}, ["text"]),
    # Utilitaires
    _f("calculate",       "Calcule expression math",            {"expression": _s("expression")}, ["expression"]),
    _f("get_datetime",    "Date et heure actuelles"),
    _f("add_days",        "Date dans X jours",                  {"days": _i("jours")}, ["days"]),
    _f("generate_password","Genere mot de passe",               {"length": _i("longueur"), "include_symbols": _b("symboles")}),
    _f("convert_units",   "Convertit unites",                   {"value": _n("valeur"), "from_unit": _s("unite source"), "to_unit": _s("unite cible")}, ["value","from_unit","to_unit"]),
    # Archives
    _f("zip_files",       "Compresse en ZIP",                   {"files": _a("fichiers"), "output": _s("sortie")}, ["files"]),
    _f("unzip_file",      "Extrait un ZIP",                     {"path": _s("chemin"), "destination": _s("destination")}, ["path"]),
    _f("list_archive",    "Liste contenu ZIP",                  {"path": _s("chemin")}, ["path"]),
    # Images
    _f("screenshot_full", "Capture ecran complet",              {"path": _s("chemin")}),
    _f("resize_image",    "Redimensionne image",                {"path": _s("chemin"), "width": _i("largeur"), "height": _i("hauteur"), "output": _s("sortie")}, ["path"]),
    _f("get_image_info",  "Infos image (dimensions, format)",   {"path": _s("chemin")}, ["path"]),
    _f("convert_image",   "Convertit format image",             {"path": _s("chemin"), "to_format": _s("format"), "output": _s("sortie")}, ["path","to_format"]),
    # Meteo
    _f("get_weather",     "Meteo complete 3 jours",             {"location": _s("ville")}),
    _f("get_weather_simple","Meteo en une ligne",               {"location": _s("ville")}),
    # Traduction
    _f("translate",       "Traduit texte",                      {"text": _s("texte"), "to_lang": _s("langue cible"), "from_lang": _s("langue source")}, ["text","to_lang"]),
    _f("detect_language", "Detecte langue d'un texte",          {"text": _s("texte")}, ["text"]),
    # QR Code
    _f("create_qrcode",   "Genere QR code",                     {"text": _s("contenu"), "output": _s("chemin"), "size": _i("taille")}, ["text"]),
    # Planificateur
    _f("create_daily_task","Tache planifiee quotidienne",       {"name": _s("nom"), "command": _s("commande"), "hour": _i("heure"), "minute": _i("minute")}, ["name","command"]),
    _f("list_tasks",      "Liste taches planifiees Amah"),
    _f("delete_task",     "Supprime tache planifiee",           {"name": _s("nom")}, ["name"]),
    _f("run_task_now",    "Lance tache immediatement",          {"name": _s("nom")}, ["name"]),
    # Stats et version
    _f("get_stats",       "Statistiques usage outils",          {"days": _i("jours")}),
    _f("reset_stats",     "Efface statistiques usage"),
    _f("check_update",    "Verifie mises a jour Amah"),
    _f("get_current_version","Version actuelle Amah"),
    _f("get_license_info","Infos licence installation"),
    # Systeme avance (v1.4)
    _f("set_volume",      "Regle le volume systeme (0-100)",    {"level": _i("niveau 0-100")}, ["level"]),
    _f("get_audio_level", "Retourne le volume actuel (0-100)"),
    _f("mute_audio",      "Bascule le son (muet/non-muet)"),
    _f("set_brightness",  "Regle la luminosite ecran (0-100)",  {"level": _i("niveau 0-100")}, ["level"]),
    _f("get_brightness",  "Retourne la luminosite actuelle"),
    _f("wifi_toggle",     "Active ou desactive le WiFi",        {"enable": _b("true=activer, false=desactiver")}, ["enable"]),
    # Vision ecran (v1.4)
    _f("analyze_screen",  "Capture + analyse visuelle de l'ecran par IA (Groq vision)", {"question": _s("question sur l'ecran")}),
    # YouTube (v1.4)
    _f("open_youtube",    "Ouvre YouTube avec une recherche dans le navigateur", {"query": _s("recherche")}, ["query"]),
    _f("search_youtube",  "Cherche des videos YouTube (sans ouvrir le navigateur)", {"query": _s("recherche"), "num_results": _i("nb resultats")}, ["query"]),
    # Vols (v1.4)
    _f("search_flights",  "Recherche des vols + ouvre Google Flights", {"from_city": _s("ville depart"), "to_city": _s("ville arrivee"), "date": _s("date ex: 2026-07-15")}, ["from_city","to_city"]),
    # Planificateur multi-etapes (v1.4)
    _f("create_plan",     "Genere un plan JSON multi-etapes pour une tache complexe (3+ actions)", {"goal": _s("objectif detaille")}, ["goal"]),
    # Execution automatique de plan (v1.5)
    _f("execute_plan",    "Genere ET execute automatiquement un plan multi-etapes (avec retry sur echec). S'arrete et demande confirmation avant une action sensible (suppression, email, etc.) -- rappeler alors avec plan_id et confirmed=true", {"goal": _s("objectif detaille (omettre si on reprend un plan)"), "plan_id": _s("id du plan en attente de confirmation"), "confirmed": _b("true pour confirmer et executer l'etape sensible en attente")}, []),
    # YouTube musique
    _f("play_music",      "Lance une recherche musicale sur YouTube Music dans le navigateur", {"query": _s("titre artiste ou genre musical")}, ["query"]),
    # Outils code (v1.5)
    _f("write_code",      "Ecrit du code dans un fichier (py, js, html, css, etc.)",    {"filename": _s("chemin du fichier"), "code": _s("code complet"), "language": _s("langage ex: python")}, ["filename","code"]),
    _f("run_code",        "Execute un fichier Python (.py) ou JavaScript (.js) et retourne la sortie", {"path": _s("chemin du fichier a executer")}, ["path"]),
    _f("explain_code",    "Lit un fichier de code pour l'analyser et l'expliquer",       {"path": _s("chemin du fichier de code")}, ["path"]),
    # Jeux (v1.5)
    _f("open_steam",                "Ouvre l'application Steam"),
    _f("open_epic_games",           "Ouvre Epic Games Launcher"),
    _f("list_installed_steam_games","Liste les jeux Steam installes sur ce PC"),
    _f("launch_game_steam",         "Lance un jeu Steam deja installe par son nom",      {"game_name": _s("nom du jeu")}, ["game_name"]),
    _f("search_game_on_steam",      "Ouvre la recherche Steam Store pour un jeu",        {"game_name": _s("nom du jeu")}, ["game_name"]),
    _f("install_game_steam",        "Cherche un jeu sur Steam Store, ouvre sa page et lance l'installation si Steam est present", {"game_name": _s("nom du jeu")}, ["game_name"]),
    # Webcam (v1.5)
    _f("analyze_webcam",   "Capture une image via la webcam et l'analyse par IA visuelle (Groq vision)", {"question": _s("question sur ce que voit la camera")}),
    _f("start_auto_mute",  "Active la surveillance webcam : coupe le son automatiquement si plusieurs personnes sont detectees devant la camera"),
    _f("stop_auto_mute",   "Desactive la surveillance webcam auto-mute et retablit le son si besoin"),
]
