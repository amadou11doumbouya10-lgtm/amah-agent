"""Routeur d'outils partagé par gui.py, voice_fullscreen.py et agent.py.

Il remplace trois routeurs qui avaient divergé : celui de gui.py (mots-clés,
~80 % de demandes bien routées), sa copie réduite dans voice_fullscreen.py et
Router V0.4 dans agent.py (expressions exactes, ~15 %). Choisit, sans appel
LLM, le petit lot d'outils à proposer au modèle pour une demande.

Quatre niveaux :
1. Conversation pure (salutation, remerciement seuls) -> aucun outil.
2. Intentions précises (expressions de Router V0.3) -> outils prioritaires.
3. Mots-clés par catégorie et extensions de fichiers -> complètent le lot.
4. Rien de reconnu -> lot d'outils de lecture par défaut, jamais zéro outil
   (sans outil, gpt-oss répondait à vide ou inventait des noms d'outils).
"""
from __future__ import annotations

import re
import unicodedata
from difflib import get_close_matches

from tools.router_v03 import INTENT_TOOLS, detect_intents

MAX_TOOLS = 12

# Catégorie -> (outils par ordre de priorité, mots-clés). Un mot peut
# appartenir à plusieurs catégories ("lis" : fichiers et documents).
# Les mots-clés sont sans accent ; une expression de plusieurs mots est
# cherchée telle quelle dans le texte normalisé.
CATEGORIES = {
    "fichiers": (
        ("read_file", "list_files", "find_files", "write_file", "edit_file", "create_folder",
         "move_file", "delete_file", "get_folder_info", "organize_folder", "summarize"),
        "fichier fichiers dossier dossiers repertoire liste lister trouve trouver retrouve "
        "deplace deplacer organise organiser range ranger trie trier classe classer lis lire "
        "affiche afficher montre montrer contenu bureau desktop downloads telechargements "
        "taille renomme renommer supprime supprimer efface effacer copie modifie modifier "
        "remplace remplacer corrige corriger ecris ecrire insere ajoute edite editer vide enleve retire",
    ),
    "documents": (
        ("create_word", "create_pdf", "create_txt", "read_document", "summarize", "edit_pdf", "write_file"),
        "word docx pdf txt document documents rapport lettre contrat facture cv resume resumer "
        "synthese redige rediger cree creer genere generer analyse analyser motivation",
    ),
    "internet": (
        ("web_search", "read_webpage", "open_browser", "get_page_text", "click_text",
         "type_in_field", "click_element", "fill_form", "take_screenshot"),
        "web internet recherche rechercher cherche chercher site page url navigateur navigue "
        "visite google clique cliquer formulaire linkedin instagram facebook wikipedia lien|va sur",
    ),
    "email": (
        ("read_emails", "search_emails", "send_email", "draft_email", "open_browser", "get_page_text"),
        "email emails mail mails courriel courriels gmail boite inbox reception messagerie "
        "courrier envoie envoyer brouillon expediteur destinataire|piece jointe|non lu",
    ),
    "memoire": (
        ("get_memories", "save_memory", "delete_memory"),
        "memorise memoriser memoire souviens souvenir souvenirs retiens retenir rappelle note "
        "noter oublie oublier preference prefere|sur moi|de moi|garde en|n oublie pas",
    ),
    "systeme": (
        ("get_system_info", "list_processes", "get_network_info", "kill_process", "open_file", "run_command"),
        "systeme pc ordinateur ram cpu processeur disque windows processus process reseau ip "
        "configuration infos informations caracteristiques ferme fermer arrete arreter tue tuer "
        "stoppe quitte rame lent consomme commande powershell cmd terminal execute executer "
        "lance lancer ouvre ouvrir open demarre",
    ),
    "code": (
        ("write_code", "run_code", "explain_code", "write_file", "edit_file", "read_file"),
        "code coder script scripts programme programmer python javascript html css fonction "
        "debug bug compile",
    ),
    "utils": (
        ("calculate", "get_datetime", "add_days", "convert_units", "generate_password"),
        "calcule calculer calcul combien pourcentage somme total multiplie divise date heure "
        "jour jours aujourd demain semaine mois annee convertis convertir conversion km miles "
        "kilometres password|mot de passe|quel jour|quelle heure|quelle date",
    ),
    "archives": (
        ("zip_files", "unzip_file", "list_archive"),
        "zip zippe zipper compresse compresser archive archives decompresse decompresser "
        "extrais extraire dezippe rar",
    ),
    # "qr code" compte double : sinon "code" faisait gagner la catégorie code
    "qrcode": (("create_qrcode",), "qr qrcode|qr code"),
    "excel": (
        ("read_excel", "create_excel", "append_to_excel"),
        "excel tableur tableau xlsx csv feuille classeur",
    ),
    "presse_papiers": (
        ("write_clipboard", "read_clipboard"),
        "clipboard colle coller copier|presse papiers|presse papier",
    ),
    "voix_rappels": (
        ("set_reminder", "send_notification", "speak", "listen", "listen_continuous"),
        "parle parler voix ecoute micro microphone notification notifie alerte rappel rappelle "
        "previens prevenir minutes reveille|a voix haute|ecoute moi",
    ),
    "images": (
        ("resize_image", "convert_image", "get_image_info", "screenshot_full"),
        "image images photo photos redimensionne redimensionner reduis reduire agrandis "
        "pixels resolution",
    ),
    "meteo": (
        ("get_weather_simple", "get_weather"),
        "meteo temps temperature pluie pleut pleuvoir neige soleil beau chaud froid previsions "
        "climat vent",
    ),
    "langues": (
        ("translate", "detect_language"),
        "traduis traduire traduction traduit langue anglais espagnol wolof arabe allemand "
        "italien portugais chinois peul soussou malinke|comment on dit|en francais",
    ),
    "amah": (
        ("get_stats", "check_update", "get_current_version", "get_license_info", "reset_stats"),
        "statistiques stats utilise utilisation outil outils version licence cle valide update|mise a jour",
    ),
    "planif": (
        ("create_daily_task", "list_tasks", "delete_task", "run_task_now"),
        "planifie planifier planifiee tache taches chaque quotidien quotidienne matin soir "
        "automatique automatiquement cron hebdo|tous les jours",
    ),
    "materiel": (
        ("set_volume", "mute_audio", "get_audio_level", "set_brightness", "get_brightness", "wifi_toggle"),
        "volume son sonore audio muet sourdine silence luminosite lumineux lumiere sombre "
        "clarte wifi bluetooth monte baisse augmente diminue rallume eteins coupe",
    ),
    "vision": (
        ("analyze_screen", "screenshot_full"),
        "ecran vois voir regarde observe capture screenshot",
    ),
    "webcam": (("analyze_webcam", "start_auto_mute", "stop_auto_mute"), "webcam camera cam"),
    "musique": (
        ("play_music", "open_youtube", "search_youtube", "web_search"),
        "youtube yt video videos clip clips musique music chanson chansons joue jouer ecouter "
        "mets film serie album artiste playlist",
    ),
    "vols": (
        ("search_flights", "web_search", "open_browser"),
        "vol vols avion billet aeroport voyage voyager",
    ),
    "plan": (
        ("execute_plan", "create_plan"),
        "plan etapes etape organise organiser prepare preparer",
    ),
    "jeux": (
        ("open_steam", "launch_game_steam", "open_epic_games", "list_installed_steam_games",
         "search_game_on_steam", "install_game_steam"),
        "steam epic jeu jeux game games gaming fortnite minecraft gta fifa valorant counter "
        "strike roblox",
    ),
}

# Extension d'un chemin cité ("C:/x/ventes.xlsx") -> catégorie
EXTENSIONS = {
    "xlsx": "excel", "xlsm": "excel", "csv": "excel",
    "docx": "documents", "pdf": "documents", "txt": "fichiers", "md": "fichiers",
    "py": "code", "js": "code", "html": "code", "css": "code", "json": "code",
    "png": "images", "jpg": "images", "jpeg": "images", "webp": "images", "bmp": "images",
    "zip": "archives", "rar": "archives", "exe": "systeme", "bat": "systeme",
}

# Rien de reconnu : outils de lecture, sans effet de bord
DEFAULT_TOOLS = (
    "web_search", "read_webpage", "get_datetime", "calculate", "get_weather_simple",
    "translate", "get_memories", "list_files", "read_file", "get_system_info",
)

# Conversation pure : le message ne contient que ces mots
CHAT_WORDS = set(
    "bonjour bonsoir salut hello hi hey coucou yo slt bjr cc re merci mrc beaucoup mille "
    "fois amah ok okay oui non ouais daccord d accord super cool top parfait genial bien "
    "tres trop ca va et toi vous comment tu vas allez bonne nuit journee soiree au revoir "
    "a plus bientot tard ciao bye good morning thanks thank you s il te plait stp svp "
    "rien de je suis content contente desole pardon excuse moi ah oh hmm euh haha lol "
    "toujours aussi bon courage c est ma mon cher chere aujourd hui".split()
)
CHAT_SENTENCES = (
    r"(qu est ce que |que )?tu (peux|sais) faire( quoi)?( pour moi)?",
    r"qui es tu", r"tu es qui", r"comment tu t appelles", r"c est quoi ton nom",
    r"presente toi", r"parle moi de toi", r"qui t a (cree|creee|fait)",
)


def normalize(text: str) -> str:
    """Minuscules, sans accents, ponctuation et tirets remplacés par des espaces."""
    text = unicodedata.normalize("NFD", str(text or "").lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9%]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_keywords(spec: str):
    """"mot1 mot2|expression a plusieurs mots|..." -> (mots, expressions)."""
    words, phrases = set(), []
    first, *extra = spec.split("|")
    words.update(first.split())
    for chunk in (c.strip() for c in extra):
        if " " in chunk:
            phrases.append(chunk)
        elif chunk:
            words.add(chunk)
    return words, phrases


_CAT_WORDS = {}
_CAT_PHRASES = {}
for _cat, (_tools, _spec) in CATEGORIES.items():
    _CAT_WORDS[_cat], _CAT_PHRASES[_cat] = _parse_keywords(_spec)
_LEXICON = sorted(set().union(*_CAT_WORDS.values()))


def is_pure_chat(text: str) -> bool:
    """Vrai si le message n'est qu'une salutation, un remerciement ou une
    question sur Amah elle-même. "bonjour, lis mes emails" n'en est pas une."""
    norm = normalize(text)
    if not norm:
        return True
    if any(re.fullmatch(p, norm) for p in CHAT_SENTENCES):
        return True
    return all(token in CHAT_WORDS for token in norm.split())


def _fuzzy(token: str) -> str:
    """Corrige une faute de frappe vers un mot-clé proche (mots de 5 lettres et plus)."""
    if len(token) < 5 or token in CHAT_WORDS:
        return token
    match = get_close_matches(token, _LEXICON, n=1, cutoff=0.86)
    return match[0] if match else token


def _category_hits(norm: str, raw: str) -> dict:
    tokens = norm.split()
    known = set(tokens)
    corrected = {_fuzzy(t) for t in tokens if t not in _LEXICON}
    hits = {}
    for cat in CATEGORIES:
        count = len((known | corrected) & _CAT_WORDS[cat])
        padded = f" {norm} "
        count += sum(1 for phrase in _CAT_PHRASES[cat] if f" {phrase} " in padded)
        if count:
            hits[cat] = count
    for ext in re.findall(r"\.([a-z0-9]{2,4})\b", raw.lower()):
        cat = EXTENSIONS.get(ext)
        if cat:
            hits[cat] = hits.get(cat, 0) + 2
    return hits


def select_tools(text: str, tools_definitions: list, max_tools: int = MAX_TOOLS):
    """Renvoie (définitions d'outils à proposer, infos de diagnostic).

    Liste vide uniquement pour une conversation pure.
    """
    by_name = {t["function"]["name"]: t for t in tools_definitions}
    if is_pure_chat(text):
        return [], {"niveau": "conversation", "intentions": [], "categories": []}

    norm = normalize(text)
    scores = {}
    order = {}

    def add(name, points):
        if name in by_name:
            scores[name] = scores.get(name, 0) + points
            order.setdefault(name, len(order))

    intents = detect_intents(text)
    for intent in intents:
        for name in sorted(INTENT_TOOLS.get(intent, ())):
            add(name, 100)

    hits = _category_hits(norm, text)
    for cat, count in sorted(hits.items(), key=lambda item: -item[1]):
        tools = CATEGORIES[cat][0]
        for rank, name in enumerate(tools):
            # Les premiers outils d'une catégorie sont les plus probables
            add(name, 10 * count + (len(tools) - rank) * 0.1)

    if not scores:
        selected = [by_name[n] for n in DEFAULT_TOOLS if n in by_name][:max_tools]
        return selected, {"niveau": "defaut", "intentions": [], "categories": []}

    ranked = sorted(scores, key=lambda n: (-scores[n], order[n]))[:max_tools]
    level = "intentions+mots" if intents and hits else ("intentions" if intents else "mots")
    return [by_name[n] for n in ranked], {
        "niveau": level, "intentions": intents, "categories": sorted(hits, key=lambda c: -hits[c]),
    }
