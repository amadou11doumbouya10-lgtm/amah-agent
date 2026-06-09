"""
AMAH AGENT v2.0 — Interface futuriste PyQt6 (or sur noir)
Remplace gui.py (tkinter) — voir gui_old.py pour l'ancienne version de référence.
"""
import sys
import os

# Windows Long Path : PyQt6 installé hors site-packages (chemin trop long sinon)
sys.path.insert(0, r"C:\pyqt6libs")

import json
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QScrollArea, QLabel, QLineEdit, QTextEdit, QPushButton, QFrame, QMenu,
    QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import (
    Qt, QObject, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QSize, QRect,
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont, QFontDatabase, QTextCursor, QAction,
)

from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS
from tools import TOOL_FUNCTIONS
from tools.memory import save_message, load_recent_messages, cleanup_old_messages, truncate_old_tool_results

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Constantes — couleurs / polices / dimensions (thème OR sur NOIR — ne pas dériver)
# ─────────────────────────────────────────────────────────────────────────────
BG          = "#0D0D0B"
BG2         = "#121210"
BG3         = "#181815"
BG4         = "#1E1E1A"
BORDER      = "#2A2A22"
BORDER2     = "#3A3A2E"
GOLD        = "#C8A96E"
GOLD2       = "#E8C98E"
GOLD_DIM    = "#7A5F38"
GOLD_FAINT  = "#2A1F0A"
TEXT        = "#E8E0D0"
TEXT2       = "#9A9280"
TEXT3       = "#5A5448"
TEXT_TOOL   = "#9A7A45"
RED         = "#C0392B"
GREEN       = "#27AE60"
CYAN        = "#00D4FF"

FONT_MONO    = "Consolas"
FONT_UI      = "Segoe UI"

SIDEBAR_W    = 64
TOPBAR_H     = 48
INPUT_MIN_H  = 44
PANEL_W      = 340

MAX_MESSAGES = 16

# ─────────────────────────────────────────────────────────────────────────────
# Police custom — charge depuis assets/fonts si présent, sinon fallback
# ─────────────────────────────────────────────────────────────────────────────
def _load_fonts():
    fonts_dir = Path(__file__).parent / "assets" / "fonts"
    if fonts_dir.exists():
        for f in fonts_dir.glob("*.ttf"):
            QFontDatabase.addApplicationFont(str(f))


TOOL_LABELS = {
    "list_files": "lecture dossier", "organize_folder": "organisation",
    "find_files": "recherche fichier", "move_file": "deplacement",
    "create_folder": "creation dossier", "read_file": "lecture fichier",
    "get_folder_info": "infos dossier", "create_word": "creation Word",
    "create_txt": "creation TXT", "create_pdf": "creation PDF",
    "read_document": "lecture document", "web_search": "recherche web",
    "read_webpage": "lecture page", "get_system_info": "infos systeme",
    "open_file": "ouverture fichier", "run_command": "commande PowerShell",
    "save_memory": "memorisation", "get_memories": "rappel memoire",
    "delete_memory": "suppression memoire", "read_emails": "lecture emails",
    "send_email": "envoi email", "search_emails": "recherche emails",
    "open_browser": "navigation web", "click_element": "clic element",
    "fill_form": "formulaire", "take_screenshot": "capture ecran",
    "get_page_text": "lecture page web", "speak": "synthese vocale",
    "send_notification": "notification", "set_reminder": "rappel programme",
    "read_excel": "lecture Excel", "create_excel": "creation Excel",
    "append_to_excel": "ajout Excel", "write_file": "ecriture fichier",
    "edit_file": "edition fichier", "list_processes": "processus actifs",
    "get_network_info": "infos reseau", "set_volume": "reglage volume",
    "get_audio_level": "niveau volume", "mute_audio": "son muet/actif",
    "set_brightness": "luminosite ecran", "get_brightness": "lecture luminosite",
    "wifi_toggle": "WiFi on/off", "analyze_screen": "vision ecran IA",
    "open_youtube": "ouverture YouTube", "search_youtube": "recherche YouTube",
    "play_music": "lecture musique", "search_flights": "recherche vols",
    "create_plan": "planification multi-etapes", "delete_file": "suppression fichier",
    "summarize": "resume document", "draft_email": "brouillon email",
    "kill_process": "arret processus", "write_code": "ecriture code",
    "run_code": "execution code", "explain_code": "explication code",
}

# Catalogue des outils affichés dans le panneau latéral (icônes Tabler)
TOOLS_DATA = {
    "Fichiers":   [("ti-folder", "Dossiers & fichiers", "list_files / organize_folder / find_files"),
                   ("ti-file-text", "Lecture / écriture", "read_file / write_file / edit_file")],
    "Documents":  [("ti-file-word", "Word / PDF / TXT", "create_word / create_pdf / create_txt"),
                   ("ti-file-search", "Lecture documents", "read_document / summarize")],
    "Web":        [("ti-world-search", "Recherche web", "web_search / read_webpage"),
                   ("ti-browser", "Navigateur", "open_browser / click_element / fill_form")],
    "Système":    [("ti-cpu", "Infos système", "get_system_info / list_processes"),
                   ("ti-terminal-2", "Commandes", "run_command / open_file / kill_process")],
    "Mémoire":    [("ti-brain", "Mémoire persistante", "save_memory / get_memories / delete_memory")],
    "Email":      [("ti-mail", "Gmail", "read_emails / send_email / search_emails / draft_email")],
    "Voix":       [("ti-microphone", "Voix & écoute", "speak / listen / listen_continuous")],
    "Hardware":   [("ti-volume", "Audio / écran / réseau",
                    "set_volume / set_brightness / wifi_toggle")],
    "Multimédia": [("ti-brand-youtube", "YouTube & musique", "open_youtube / search_youtube / play_music"),
                   ("ti-cloud", "Météo & traduction", "get_weather / translate")],
    "Code":       [("ti-code", "Outils développeur", "write_code / run_code / explain_code")],
}


# ═════════════════════════════════════════════════════════════════════════════
# Moteur de chat — porté depuis gui.py, exécuté dans un QThread
# ═════════════════════════════════════════════════════════════════════════════
class ChatEngine(QObject):
    thinking      = pyqtSignal(str)            # message de statut
    tool_used     = pyqtSignal(str)            # libellé d'outil utilisé
    reply_ready   = pyqtSignal(str)            # réponse finale complète
    error_raised  = pyqtSignal(str)            # message d'erreur formaté

    _WORD_TO_CAT = {
        "liste":"fichiers","lister":"fichiers","fichier":"fichiers","fichiers":"fichiers",
        "dossier":"fichiers","dossiers":"fichiers","trouve":"fichiers","trouver":"fichiers",
        "deplace":"fichiers","organise":"fichiers","organiser":"fichiers","classe":"fichiers",
        "lis":"fichiers","lire":"fichiers","lit":"fichiers","affiche":"fichiers",
        "montre":"fichiers","montre-moi":"fichiers","montrer":"fichiers","vois":"fichiers",
        "find":"fichiers","read":"fichiers","bureau":"fichiers","desktop":"fichiers",
        "downloads":"fichiers","telechargements":"fichiers","taille":"fichiers",
        "renomme":"fichiers","supprime":"fichiers","copie":"fichiers",
        "modifie":"fichiers","modifier":"fichiers","change":"fichiers","changer":"fichiers",
        "ecris":"fichiers","ecrire":"fichiers","remplace":"fichiers","remplacer":"fichiers",
        "corrige":"fichiers","corriger":"fichiers","mets":"fichiers","mettre":"fichiers",
        "insere":"fichiers","inserer":"fichiers","ajoute":"fichiers","ajouter":"fichiers",
        "edite":"fichiers","editer":"fichiers",
        "html":"fichiers","htm":"fichiers","index":"fichiers","css":"fichiers",
        "js":"fichiers","py":"fichiers","json":"fichiers","xml":"fichiers",
        "csv":"fichiers","log":"fichiers","ini":"fichiers","cfg":"fichiers",
        "exe":"fichiers","bat":"fichiers","sh":"fichiers","md":"fichiers",
        "word":"documents","pdf":"documents","txt":"documents","document":"documents",
        "rapport":"documents","cree":"documents","creer":"documents","genere":"documents",
        "generer":"documents","redige":"documents","rediger":"documents","ecrit":"documents",
        "prepare":"documents","write":"documents","create":"documents","make":"documents",
        "resume":"documents","synthese":"documents","lettre":"documents",
        "contrat":"documents","facture":"documents",
        "web":"internet","recherche":"internet","rechercher":"internet","site":"internet",
        "navigateur":"internet","visite":"internet","cherche":"internet","chercher":"internet",
        "url":"internet","click":"internet","clique":"internet","screenshot":"internet",
        "capture":"internet","telecharge":"internet","linkedin":"internet","google":"internet",
        "instagram":"internet","navigue":"internet","page":"internet","contenu":"internet",
        "scrape":"internet",
        "ouvre":"systeme","ouvrir":"systeme","open":"systeme","va":"systeme","vas":"systeme",
        "lance":"systeme","lancer":"systeme","afficher":"systeme",
        "editeur":"systeme","vscode":"systeme","notepad":"systeme",
        "email":"email","emails":"email","mail":"email","mails":"email","boite":"email",
        "envoie":"email","envoyer":"email","send":"email","gmail":"email","message":"email",
        "reponse":"email","repond":"email","expediteur":"email","sujet":"email",
        "piece":"email","jointe":"email","inbox":"email","reception":"email",
        "nouveau":"email","nouveaux":"email","non-lu":"email","nonlu":"email",
        "messagerie":"email","courrier":"email","courriel":"email","brouillon":"email",
        "draft":"email",
        "memorise":"memoire","souviens":"memoire","rappelle":"memoire","memoire":"memoire",
        "retiens":"memoire","note":"memoire","notes":"memoire","oublie":"memoire",
        "sais":"memoire","sait":"memoire","preference":"memoire","info":"memoire",
        "systeme":"systeme","processus":"systeme","process":"systeme","reseau":"systeme",
        "ip":"systeme","commande":"systeme","run":"systeme","execute":"systeme",
        "ferme":"systeme","ram":"systeme","cpu":"systeme","disque":"systeme",
        "windows":"systeme","pc":"systeme","ordinateur":"systeme","tuer":"systeme",
        "stoppe":"systeme","stopper":"systeme","termine":"systeme","terminer":"systeme",
        "quitte":"systeme","coupe":"systeme","fige":"systeme","plante":"systeme","bloque":"systeme",
        "calcule":"utils","calculer":"utils","convertis":"utils","convertir":"utils",
        "date":"utils","heure":"utils","password":"utils","passe":"utils",
        "zip":"utils","archive":"utils","qr":"utils","qrcode":"utils",
        "combien":"utils","quel":"utils","quand":"utils","dans":"utils","depuis":"utils",
        "jours":"utils","mois":"utils","annee":"utils",
        "excel":"data","tableau":"data","tableur":"data","xlsx":"data",
        "clipboard":"data","presse-papiers":"data","copier":"data","coller":"data","presse":"data",
        "parle":"media","dis":"media","dis-moi":"media","voix":"media","speak":"media",
        "ecoute":"media","microphone":"media","micro":"media","notification":"media",
        "notifie":"media","alerte":"media","rappel":"media","rappelle-moi":"media","bip":"media",
        "ecran":"media",
        "image":"images","images":"images","photo":"images","photos":"images",
        "redimensionne":"images","resize":"images","png":"images","jpg":"images",
        "jpeg":"images","webp":"images","bmp":"images",
        "meteo":"info","temps":"info","temperature":"info","previsions":"info",
        "traduis":"info","traduire":"info","traduction":"info","langue":"info","translate":"info",
        "stats":"info","statistiques":"info","version":"info","licence":"info",
        "mise-a-jour":"info","update":"info","pluie":"info","soleil":"info",
        "planifie":"planif","planifier":"planif","tache":"planif","taches":"planif",
        "planificateur":"planif","cron":"planif","automatique":"planif","chaque":"planif",
        "quotidien":"planif","hebdo":"planif","programme":"planif",
        "volume":"hardware","son":"hardware","audio":"hardware","muet":"hardware",
        "silence":"hardware","sourd":"hardware","bascule":"hardware",
        "lumiere":"hardware","luminosite":"hardware","lumineux":"hardware","sombre":"hardware",
        "clarte":"hardware","eclairer":"hardware","assombrir":"hardware",
        "wifi":"hardware","wi-fi":"hardware","sans-fil":"hardware","wlan":"hardware",
        "bluetooth":"hardware",
        "vois-ecran":"vision","regarde-ecran":"vision","observe":"vision",
        "analyse-mon-ecran":"vision","que-vois-tu":"vision","vision":"vision",
        "vois-tu":"vision","regardes":"vision","captur":"vision",
        "youtube":"youtube","yt":"youtube","video":"youtube","videos":"youtube",
        "musique":"youtube","chanson":"youtube","chansons":"youtube",
        "film":"youtube","films":"youtube","serie":"youtube","clip":"youtube",
        "joue":"youtube","jouer":"youtube","ecouter":"youtube","écoute":"youtube",
        "music":"youtube","song":"youtube","play":"youtube",
        "vol":"flights","vols":"flights","avion":"flights","avions":"flights",
        "billet":"flights","aeroport":"flights","voyage":"flights","voyager":"flights",
        "depart":"flights","arrivee":"flights","aller":"flights","retour":"flights",
        "skyscanner":"flights","kayak":"flights","booking":"flights",
        "plan":"planner","etapes":"planner","sequence":"planner","multi-etapes":"planner",
        "code":"code","coder":"code","programmer":"code","script":"code",
        "executer":"code","exécute":"code","exécuter":"code","python":"code",
        "javascript":"code","node":"code","debug":"code","debugue":"code",
    }

    _CAT_TOOLS = {
        "fichiers":  {"list_files","organize_folder","find_files","move_file","create_folder","read_file","write_file","edit_file","edit_pdf","get_folder_info","delete_file","summarize"},
        "documents": {"create_word","create_txt","create_pdf","read_document","write_file","edit_file","edit_pdf","summarize"},
        "internet":  {"web_search","read_webpage","open_browser","click_element","fill_form","take_screenshot","get_page_text"},
        "email":     {"read_emails","send_email","search_emails","draft_email"},
        "memoire":   {"save_memory","get_memories","delete_memory"},
        "systeme":   {"get_system_info","open_file","run_command","list_processes","get_network_info","kill_process"},
        "code":      {"write_code","run_code","explain_code","read_file","write_file","edit_file"},
        "utils":     {"calculate","get_datetime","add_days","generate_password","convert_units","zip_files","unzip_file","list_archive","create_qrcode"},
        "data":      {"read_excel","create_excel","append_to_excel","read_clipboard","write_clipboard"},
        "media":     {"speak","listen","listen_continuous","send_notification","set_reminder","screenshot_full"},
        "images":    {"resize_image","get_image_info","convert_image"},
        "info":      {"get_weather","get_weather_simple","translate","detect_language","get_stats","check_update","get_current_version","get_license_info"},
        "planif":    {"create_daily_task","list_tasks","delete_task","run_task_now"},
        "hardware":  {"set_volume","get_audio_level","mute_audio","set_brightness","get_brightness","wifi_toggle"},
        "vision":    {"analyze_screen","screenshot_full"},
        "youtube":   {"open_youtube","search_youtube","play_music","open_browser","web_search"},
        "flights":   {"search_flights","web_search","open_browser"},
        "planner":   {"create_plan"},
    }

    DEFAULT_TOOLS = {
        "web_search","read_webpage","list_files","read_file",
        "open_file","run_command","create_word","get_datetime","calculate",
        "save_memory","get_memories","read_emails","send_email",
        "get_system_info","speak",
        "get_weather","get_weather_simple",
        "translate","open_youtube","play_music",
    }

    SIMPLE_PATTERNS = {
        "bonjour","bonsoir","salut","hello","hi","merci","ok","oui","non",
        "comment","quoi","qui","quand","pourquoi","combien","cest","cest-quoi",
        "explique","dis","repete","aide","help","test","essai",
    }

    def __init__(self):
        super().__init__()
        self._api_keys = [k for k in [
            os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2"), os.getenv("GROQ_API_KEY_3"),
        ] if k and not k.startswith("AJOUTER")]
        if not self._api_keys:
            raise RuntimeError("GROQ_API_KEY introuvable dans le fichier .env")

        self._key_index = 0
        self.client     = Groq(api_key=self._api_keys[0])
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._tools_this_call = []

        cleanup_old_messages(days=90)
        truncate_old_tool_results(max_chars=800)
        previous = load_recent_messages(limit=10)
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}] + previous

    # ── Sélection ciblée des outils (normalisation accents) ─────────────────
    def _select_tools(self, message: str):
        nfd = unicodedata.normalize("NFD", message.lower().replace("'", " "))
        clean = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        words = clean.split()
        cats = set()
        for w in words:
            cat = self._WORD_TO_CAT.get(w)
            if cat:
                cats.add(cat)
        if not cats:
            return None
        needed = set()
        for cat in cats:
            needed |= self._CAT_TOOLS.get(cat, set())
        return [t for t in TOOLS_DEFINITIONS if t["function"]["name"] in needed]

    def _trim_messages(self):
        if len(self.messages) <= MAX_MESSAGES + 1:
            return
        system = self.messages[0]
        tail   = self.messages[-MAX_MESSAGES:]
        while tail and tail[0].get("role") == "tool":
            tail = tail[1:]
        self.messages = [system] + tail

    def _next_key(self):
        nb = len(self._api_keys)
        if nb <= 1:
            return False
        self._key_index = (self._key_index + 1) % nb
        self.client = Groq(api_key=self._api_keys[self._key_index])
        return True

    def _groq_call(self, messages, tools=None, model_override=None):
        used_model = model_override or MODEL
        kwargs = dict(model=used_model, messages=messages, max_tokens=1024, temperature=0.4)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        keys_tried = 0
        delays = [1, 2, 4]
        for attempt in range(len(delays) * len(self._api_keys)):
            try:
                return self.client.chat.completions.create(**kwargs)
            except Exception as e:
                err = str(e)
                is_limit = "429" in err or "rate_limit" in err or "TPD" in err or "TPM" in err
                if is_limit:
                    if keys_tried < len(self._api_keys) - 1 and self._next_key():
                        keys_tried += 1
                        nb = len(self._api_keys)
                        self.thinking.emit(f"Cle {self._key_index + 1}/{nb} — limite atteinte, rotation...")
                        continue
                    delay = delays[min(attempt, len(delays) - 1)]
                    self.thinking.emit(f"Toutes les cles limitees — attente {delay}s...")
                    time.sleep(delay)
                elif "503" in err:
                    time.sleep(delays[min(attempt, len(delays) - 1)])
                else:
                    raise

    def _execute_tool(self, tool_call) -> str:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments) or {}
        except Exception:
            args = {}
        if not isinstance(args, dict):
            args = {}

        func = TOOL_FUNCTIONS.get(name)
        if not func:
            return json.dumps({"error": f"Outil inconnu: {name}"}, ensure_ascii=False)

        label = TOOL_LABELS.get(name, name)
        self._tools_this_call.append(label)
        self.tool_used.emit(label)
        self.thinking.emit(f"Outil : {label}...")

        try:
            result = func(**args)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _format_error(self, error: str) -> str:
        if "rate_limit_exceeded" in error or "Rate limit" in error:
            import re
            wait = re.search(r"try again in (.+?)\.", error)
            temps = wait.group(1) if wait else "quelques minutes"
            return (f"Limite quotidienne Groq atteinte.\nAttends {temps} avant de continuer.\n"
                    f"Ou cree un 2eme compte gratuit sur console.groq.com")
        if "invalid_api_key" in error or "API key" in error.lower():
            return "Cle API Groq invalide. Verifie ta cle dans le fichier .env"
        if "connection" in error.lower() or "network" in error.lower():
            return "Pas de connexion internet. Verifie ta connexion et reessaie."
        if "timeout" in error.lower():
            return "La requete a pris trop de temps. Reessaie dans un moment."
        return error

    def _run_inner(self) -> str:
        self._trim_messages()
        last_user = next((m["content"] for m in reversed(self.messages) if m["role"] == "user"), "")
        tools = self._select_tools(last_user)

        words_lower = set(last_user.lower().replace("'", " ").split())
        is_simple = (len(last_user.split()) <= 6
                     and bool(words_lower & self.SIMPLE_PATTERNS)
                     and not tools)

        if is_simple:
            active_model = "llama-3.1-8b-instant"
            self.thinking.emit("Amah reflechit...")
        elif not tools:
            active_model = MODEL
            tools = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] in self.DEFAULT_TOOLS]
            self.thinking.emit("Amah reflechit...")
        else:
            active_model = MODEL
            self.thinking.emit("Amah reflechit (outils cibles)...")

        response = self._groq_call(self.messages, tools=tools, model_override=active_model)

        if response.choices[0].finish_reason == "tool_calls":
            tool_names = {tc.function.name for tc in (response.choices[0].message.tool_calls or [])}
            available  = {t["function"]["name"] for t in (tools or [])}
            if not tool_names.issubset(available):
                response = self._groq_call(self.messages, tools=TOOLS_DEFINITIONS, model_override=MODEL)

        while response.choices[0].finish_reason == "tool_calls":
            msg = response.choices[0].message
            if not msg.tool_calls:
                break

            self.messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            })

            for tc in msg.tool_calls:
                result = self._execute_tool(tc)
                if len(result) > 2000:
                    result = result[:2000] + "\n...[tronqué pour économiser les tokens]"
                self.messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

            self._trim_messages()
            response = self._groq_call(self.messages, tools=TOOLS_DEFINITIONS, model_override=MODEL)

        return response.choices[0].message.content

    # ── Point d'entrée appelé depuis le thread de travail ───────────────────
    def send(self, text: str):
        self._tools_this_call = []
        self.messages.append({"role": "user", "content": text})
        save_message(self.session_id, "user", text)
        try:
            reply = self._run_inner()
            self.messages.append({"role": "assistant", "content": reply})
            save_message(self.session_id, "assistant", reply)
            self.reply_ready.emit(reply or "")
        except Exception as e:
            self.error_raised.emit(self._format_error(str(e)))


class ChatWorker(QThread):
    """Exécute une requête ChatEngine.send() hors du thread UI."""
    def __init__(self, engine: ChatEngine, text: str):
        super().__init__()
        self.engine = engine
        self.text   = text

    def run(self):
        self.engine.send(self.text)


# ═════════════════════════════════════════════════════════════════════════════
# StatusIndicator — point pulsant animé (IDLE / THINKING / STREAMING / ERROR)
# ═════════════════════════════════════════════════════════════════════════════
class StatusIndicator(QWidget):
    _COLORS = {"IDLE": GREEN, "THINKING": GOLD, "STREAMING": CYAN, "ERROR": RED}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self.setStyleSheet("background: transparent;")
        self._state  = "IDLE"
        self._phase  = 0.0
        self._timer  = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    def set_state(self, state: str):
        if state in self._COLORS:
            self._state = state
            self._phase = 0.0

    def _tick(self):
        self._phase = (self._phase + 0.08) % (2 * 3.14159265)
        self.update()

    def paintEvent(self, _event):
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._COLORS.get(self._state, GREEN))
        pulse = 0.5 + 0.5 * math.sin(self._phase)

        # halo pulsant
        halo = QColor(color)
        halo.setAlphaF(0.18 + 0.18 * pulse)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(halo))
        r = 5 + 3 * pulse
        cx, cy = self.width() / 2, self.height() / 2
        p.drawEllipse(QPoint(int(cx), int(cy)), int(r + 3), int(r + 3))

        # point central
        p.setBrush(QBrush(color))
        p.drawEllipse(QPoint(int(cx), int(cy)), 4, 4)


class ModelPill(QWidget):
    def __init__(self, text="Groq 70B/8B", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 3, 10, 3)
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{TEXT3}; background:transparent; font-family:'{FONT_MONO}'; font-size:8pt;")
        lay.addWidget(lbl)
        self.setStyleSheet(f"background:{BORDER}; border-radius:4px;")


# ═════════════════════════════════════════════════════════════════════════════
# TopBar
# ═════════════════════════════════════════════════════════════════════════════
class TopBarActions(QWidget):
    mic_clicked      = pyqtSignal()
    copy_clicked     = pyqtSignal()
    reset_clicked    = pyqtSignal()
    amah_clicked     = pyqtSignal()
    listener_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self._btn("◎ mic",    GOLD_DIM, BG2, self.mic_clicked))
        lay.addWidget(self._btn("⎘ copier", TEXT2,    BG2, self.copy_clicked))
        lay.addWidget(self._btn("⟳ reset",  TEXT2,    BG2, self.reset_clicked))
        lay.addWidget(self._btn("◉ AMAH", GOLD,     GOLD_FAINT, self.amah_clicked, bold=True))
        lay.addWidget(self._btn("⬡ écoute", CYAN,     "#0A1020", self.listener_clicked))

    def _btn(self, text, fg, bg, signal, bold=False):
        b = QPushButton(text)
        weight = "bold" if bold else "normal"
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton {{
                color: {fg}; background: {bg}; border: 1px solid {BORDER};
                border-radius: 4px; padding: 5px 10px;
                font-family: '{FONT_MONO}'; font-size: 9pt; font-weight: {weight};
            }}
            QPushButton:hover {{ background: {BG4}; color: {GOLD2}; border-color: {BORDER2}; }}
        """)
        b.clicked.connect(signal.emit)
        return b


class TopBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(TOPBAR_H)
        self.setStyleSheet(f"background:{BG2}; border-bottom: 1px solid {BORDER};")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 14, 0)

        self.indicator = StatusIndicator(self)
        self.status_lbl = QLabel("AMAH // PRET")
        self.status_lbl.setStyleSheet(f"color:{TEXT2}; background:transparent; font-family:'{FONT_MONO}'; font-size:9pt;")

        lay.addWidget(self.indicator)
        lay.addSpacing(8)
        lay.addWidget(self.status_lbl)
        lay.addStretch()

        self.model_pill = ModelPill()
        self.actions    = TopBarActions(self)
        lay.addWidget(self.model_pill)
        lay.addSpacing(8)
        lay.addWidget(self.actions)

    def set_status(self, text: str, state: str = None):
        self.status_lbl.setText(text)
        if state:
            self.indicator.set_state(state)


# ═════════════════════════════════════════════════════════════════════════════
# Chat — bulles de message + pastilles d'outil + machine à écrire
# ═════════════════════════════════════════════════════════════════════════════
class ToolPill(QLabel):
    def __init__(self, label: str, parent=None):
        super().__init__(f"⚙ {label}", parent)
        self.setStyleSheet(f"""
            color: {TEXT_TOOL}; background: {GOLD_FAINT};
            border: 1px solid {BORDER2}; border-radius: 9px;
            padding: 2px 9px; font-family:'{FONT_MONO}'; font-size: 8pt; font-style: italic;
        """)


class MessageGroup(QWidget):
    """Un bloc de message : étiquette horodatée + texte + (outils utilisés)."""
    def __init__(self, who: str, color: str, parent=None):
        super().__init__(parent)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(20, 6, 20, 6)
        self._lay.setSpacing(4)

        head = QHBoxLayout()
        ts = datetime.now().strftime("%H:%M:%S")
        self.ts_lbl  = QLabel(f"[{ts}]")
        self.ts_lbl.setStyleSheet(f"color:{TEXT3}; background:transparent; font-family:'{FONT_MONO}'; font-size:8pt;")
        self.who_lbl = QLabel(who)
        self.who_lbl.setStyleSheet(f"color:{color}; background:transparent; font-family:'{FONT_MONO}'; font-size:10pt; font-weight:bold;")
        head.addWidget(self.ts_lbl)
        head.addSpacing(6)
        head.addWidget(self.who_lbl)
        head.addStretch()
        self._lay.addLayout(head)

        self.text_lbl = QLabel("")
        self.text_lbl.setWordWrap(True)
        self.text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.text_lbl.setStyleSheet(f"color:{TEXT}; background:transparent; font-family:'{FONT_MONO}'; font-size:10.5pt;")
        self._lay.addWidget(self.text_lbl)

        self.tools_row = QHBoxLayout()
        self.tools_row.setSpacing(5)
        self.tools_row.addStretch(0)
        self._tools_holder = QWidget()
        self._tools_holder.setLayout(self.tools_row)
        self._tools_holder.hide()
        self._lay.addWidget(self._tools_holder)

    def set_text(self, text: str):
        self.text_lbl.setText(text)

    def append_text(self, chunk: str):
        self.text_lbl.setText(self.text_lbl.text() + chunk)

    def add_tool_pills(self, labels):
        if not labels:
            return
        # vide la rangée existante
        while self.tools_row.count() > 0:
            item = self.tools_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for lbl in labels:
            self.tools_row.addWidget(ToolPill(lbl))
        self.tools_row.addStretch()
        self._tools_holder.show()


class ChatWidget(QScrollArea):
    """Zone de conversation défilante avec effet scan-lines discret."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(f"QScrollArea {{ background:{BG}; border:none; }}")

        self._inner = QWidget()
        self._inner.setStyleSheet(f"background:{BG};")
        self._vlay = QVBoxLayout(self._inner)
        self._vlay.setContentsMargins(0, 14, 0, 14)
        self._vlay.setSpacing(2)
        self._vlay.addStretch()
        self.setWidget(self._inner)

        self._typer_timer = QTimer(self)
        self._typer_timer.timeout.connect(self._typer_tick)
        self._typer_buffer = ""
        self._typer_target = None
        self._typer_idx    = 0

    # ── API publique ─────────────────────────────────────────────────────
    def add_user_message(self, text: str):
        grp = MessageGroup("Toi  >", TEXT2)
        grp.set_text(text)
        self._insert(grp)

    def start_amah_message(self):
        grp = MessageGroup("Amah >", GOLD)
        grp.set_text("")
        self._insert(grp)
        self._current_amah = grp
        return grp

    def stream_token(self, token: str):
        if getattr(self, "_current_amah", None):
            self._current_amah.append_text(token)
            self._scroll_bottom()

    def end_amah_message(self, full_text: str, tools=None):
        grp = getattr(self, "_current_amah", None)
        if grp is None:
            grp = self.start_amah_message()
        self._typewrite(grp, full_text, tools or [])

    def add_system_line(self, text: str, color: str = TEXT3):
        lbl = QLabel(text)
        lbl.setContentsMargins(20, 2, 20, 2)
        lbl.setStyleSheet(f"color:{color}; background:transparent; font-family:'{FONT_MONO}'; font-size:8pt; font-style: italic;")
        self._insert(lbl)

    def clear(self):
        while self._vlay.count() > 1:
            item = self._vlay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._current_amah = None

    # ── interne ──────────────────────────────────────────────────────────
    def _insert(self, widget):
        self._vlay.insertWidget(self._vlay.count() - 1, widget)
        self._scroll_bottom()

    def _scroll_bottom(self):
        bar = self.verticalScrollBar()
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

    def _typewrite(self, group: MessageGroup, text: str, tools):
        self._typer_target = group
        self._typer_full   = text
        self._typer_idx    = 0
        self._typer_tools  = tools
        n_ticks = 60
        self._typer_chunk  = max(1, len(text) // n_ticks)
        group.set_text("")
        self._typer_timer.start(20)

    def _typer_tick(self):
        grp  = self._typer_target
        text = self._typer_full
        if grp is None:
            self._typer_timer.stop()
            return
        end = min(self._typer_idx + self._typer_chunk, len(text))
        grp.set_text(text[:end])
        self._typer_idx = end
        self._scroll_bottom()
        if end >= len(text):
            self._typer_timer.stop()
            grp.add_tool_pills(self._typer_tools)
            self._current_amah = None

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(QColor(GOLD))
        pen.setWidth(1)
        c = QColor(GOLD)
        c.setAlpha(8)
        pen.setColor(c)
        painter.setPen(pen)
        h = self.viewport().height()
        w = self.viewport().width()
        for y in range(0, h, 3):
            painter.drawLine(0, y, w, y)


# ═════════════════════════════════════════════════════════════════════════════
# Suggestions
# ═════════════════════════════════════════════════════════════════════════════
class SugChip(QPushButton):
    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                color:{TEXT2}; background:{BORDER}; border:none; border-radius:4px;
                padding:5px 12px; font-family:'{FONT_MONO}'; font-size:8pt;
            }}
            QPushButton:hover {{ background:{BORDER2}; color:{GOLD}; }}
        """)


class SuggestionsBar(QWidget):
    suggestion_clicked = pyqtSignal(str)

    _CHIPS = [
        ("⊡ bureau",  "Organise mon bureau"),
        ("✉ emails",  "Lis mes 5 derniers emails"),
        ("☁ météo",   "Météo Paris aujourd'hui"),
        ("▤ Word",    "Crée un document Word"),
        ("⌕ web",     "Recherche le web"),
        ("♪ musique", "Mets de la musique"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER}; border-bottom:1px solid {BORDER};")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 6, 14, 6)
        lay.setSpacing(8)
        for label, query in self._CHIPS:
            chip = SugChip(label)
            chip.clicked.connect(lambda _=False, q=query: self.suggestion_clicked.emit(q))
            lay.addWidget(chip)
        lay.addStretch()


# ═════════════════════════════════════════════════════════════════════════════
# Input bar — zone de texte avec décorations dorées dans les coins
# ═════════════════════════════════════════════════════════════════════════════
class InputBox(QTextEdit):
    submit = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Écris à Amah…")
        self.setFixedHeight(INPUT_MIN_H)
        self.setStyleSheet(f"""
            QTextEdit {{
                background:{BG3}; color:{TEXT}; border:none;
                font-family:'{FONT_MONO}'; font-size:10.5pt; padding: 10px 14px;
            }}
        """)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
                not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submit.emit()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(GOLD_DIM))
        pen.setWidth(2)
        painter.setPen(pen)
        s = 10
        w, h = self.width(), self.height()
        # coin haut-gauche
        painter.drawLine(2, 2, 2 + s, 2)
        painter.drawLine(2, 2, 2, 2 + s)
        # coin bas-droit
        painter.drawLine(w - 3, h - 3, w - 3 - s, h - 3)
        painter.drawLine(w - 3, h - 3, w - 3, h - 3 - s)


class InputBar(QWidget):
    message_sent  = pyqtSignal(str)
    mic_toggled   = pyqtSignal()
    file_attached = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG};")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 10, 16, 10)

        wrap = QFrame()
        wrap.setStyleSheet(f"background:{BG3}; border:1px solid {BORDER2}; border-radius:6px;")
        row = QHBoxLayout(wrap)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(4)

        self.attach_btn = self._icon_btn("📎", "Joindre un fichier")
        self.attach_btn.clicked.connect(self.file_attached.emit)

        self.box = InputBox()
        self.box.submit.connect(self._send)

        self.mic_btn  = self._icon_btn("◎", "Micro", color=GOLD_DIM)
        self.mic_btn.clicked.connect(self.mic_toggled.emit)

        self.send_btn = QPushButton("➤")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFixedSize(36, 36)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                color:{BG}; background:{GOLD}; border:none; border-radius:18px;
                font-size: 13pt; font-weight:bold;
            }}
            QPushButton:hover {{ background:{GOLD2}; }}
            QPushButton:disabled {{ background:{GOLD_DIM}; color:{BG2}; }}
        """)
        self.send_btn.clicked.connect(self._send)

        row.addWidget(self.attach_btn)
        row.addWidget(self.box, 1)
        row.addWidget(self.mic_btn)
        row.addWidget(self.send_btn)
        outer.addWidget(wrap)

    def _icon_btn(self, glyph, tooltip, color=TEXT2):
        b = QPushButton(glyph)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setToolTip(tooltip)
        b.setFixedSize(36, 36)
        b.setStyleSheet(f"""
            QPushButton {{
                color:{color}; background:transparent; border:none; border-radius:6px;
                font-size: 12pt;
            }}
            QPushButton:hover {{ background:{BG4}; color:{GOLD}; }}
        """)
        return b

    def _send(self):
        text = self.box.toPlainText().strip()
        if not text:
            return
        self.box.clear()
        self.message_sent.emit(text)

    def set_busy(self, busy: bool):
        self.send_btn.setEnabled(not busy)
        self.box.setEnabled(not busy)


# ═════════════════════════════════════════════════════════════════════════════
# Tools panel — panneau coulissant avec recherche
# ═════════════════════════════════════════════════════════════════════════════
class PanelHeader(QWidget):
    close_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 10, 12)
        title = QLabel("⚙ Outils d'Amah")
        title.setStyleSheet(f"color:{GOLD}; background:transparent; font-family:'{FONT_MONO}'; font-size:11pt; font-weight:bold;")
        close = QPushButton("✕")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setFixedSize(28, 28)
        close.setStyleSheet(f"""
            QPushButton {{ color:{TEXT2}; background:transparent; border:none; font-size:11pt; }}
            QPushButton:hover {{ color:{GOLD}; }}
        """)
        close.clicked.connect(self.close_clicked.emit)
        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(close)


class SearchBox(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Rechercher un outil…")
        self.setStyleSheet(f"""
            QLineEdit {{
                background:{BG3}; color:{TEXT}; border:1px solid {BORDER};
                border-radius:5px; padding:7px 10px; font-family:'{FONT_MONO}'; font-size:9pt;
            }}
            QLineEdit:focus {{ border-color:{GOLD_DIM}; }}
        """)


class ToolCategoryLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(f"color:{TEXT3}; background:transparent; font-family:'{FONT_MONO}'; font-size:8pt; "
                           f"font-weight:bold; letter-spacing:1px; padding-top:8px;")


class ToolItem(QFrame):
    clicked_item = pyqtSignal(str)

    def __init__(self, icon, name, desc, parent=None):
        super().__init__(parent)
        self._name = name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{ background:{BG3}; border:1px solid {BORDER}; border-radius:5px; }}
            QFrame:hover {{ border-color:{GOLD_DIM}; background:{BG4}; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(2)
        nm = QLabel(f"{icon}  {name}")
        nm.setStyleSheet(f"color:{TEXT}; background:transparent; font-family:'{FONT_MONO}'; font-size:9.5pt; font-weight:bold; border:none;")
        ds = QLabel(desc)
        ds.setStyleSheet(f"color:{TEXT3}; background:transparent; font-family:'{FONT_MONO}'; font-size:8pt; border:none;")
        ds.setWordWrap(True)
        lay.addWidget(nm)
        lay.addWidget(ds)
        self._search_blob = f"{name} {desc}".lower()

    def mousePressEvent(self, event):
        self.clicked_item.emit(self._name)
        super().mousePressEvent(event)

    def matches(self, query: str) -> bool:
        return query in self._search_blob


class ToolsList(QScrollArea):
    tool_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(f"QScrollArea {{ background:{BG2}; border:none; }}")
        inner = QWidget()
        inner.setStyleSheet(f"background:{BG2};")
        self._lay = QVBoxLayout(inner)
        self._lay.setContentsMargins(12, 4, 12, 12)
        self._lay.setSpacing(6)
        self._items = []

        for cat, entries in TOOLS_DATA.items():
            self._lay.addWidget(ToolCategoryLabel(cat))
            for icon, name, desc in entries:
                item = ToolItem(icon, name, desc)
                item.clicked_item.connect(self.tool_selected.emit)
                self._lay.addWidget(item)
                self._items.append(item)

        self._lay.addStretch()
        self.setWidget(inner)

    def filter(self, query: str):
        q = query.strip().lower()
        for item in self._items:
            item.setVisible(not q or item.matches(q))


class ToolsPanel(QWidget):
    """Panneau latéral coulissant (overlay) listant les outils disponibles."""
    tool_selected = pyqtSignal(str)
    closed        = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(PANEL_W)
        self.setStyleSheet(f"background:{BG2}; border-left:1px solid {BORDER2};")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.header = PanelHeader()
        self.header.close_clicked.connect(self.hide_panel)

        self.search = SearchBox()
        self.search.textChanged.connect(self._on_search)

        search_wrap = QWidget()
        sw_lay = QHBoxLayout(search_wrap)
        sw_lay.setContentsMargins(14, 0, 14, 10)
        sw_lay.addWidget(self.search)

        self.list = ToolsList()
        self.list.tool_selected.connect(self.tool_selected.emit)

        lay.addWidget(self.header)
        lay.addWidget(search_wrap)
        lay.addWidget(self.list, 1)

        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.hide()

    def _on_search(self, text):
        self.list.filter(text)

    def _panel_y(self):
        return TOPBAR_H

    def _panel_height(self, parent):
        return parent.height() - TOPBAR_H

    def show_panel(self):
        parent = self.parentWidget()
        if not parent:
            return
        y = self._panel_y()
        target_x = parent.width() - self.width()
        self.setGeometry(parent.width(), y, self.width(), self._panel_height(parent))
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(QPoint(parent.width(), y))
        self._anim.setEndValue(QPoint(target_x, y))
        self._anim.start()

    def hide_panel(self):
        parent = self.parentWidget()
        if not parent:
            self.hide()
            return
        self._anim.stop()
        self._anim.setStartValue(self.pos())
        self._anim.setEndValue(QPoint(parent.width(), self._panel_y()))
        try:
            self._anim.finished.disconnect()
        except TypeError:
            pass
        self._anim.finished.connect(self._finish_hide)
        self._anim.start()

    def _finish_hide(self):
        self.hide()
        self.closed.emit()
        try:
            self._anim.finished.disconnect(self._finish_hide)
        except TypeError:
            pass

    def toggle(self):
        if self.isVisible():
            self.hide_panel()
        else:
            self.show_panel()


# ═════════════════════════════════════════════════════════════════════════════
# Sidebar
# ═════════════════════════════════════════════════════════════════════════════
class SidebarWidget(QWidget):
    tools_toggled    = pyqtSignal()
    history_clicked  = pyqtSignal()
    memory_clicked   = pyqtSignal()
    files_clicked    = pyqtSignal()
    settings_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_W)
        self.setStyleSheet(f"background:{BG2}; border-right:1px solid {BORDER};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 10, 4, 12)
        lay.setSpacing(2)

        logo = QLabel("⬡")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"color:{GOLD}; background:transparent; font-size:18pt; font-family:'{FONT_MONO}';")
        lay.addWidget(logo)
        lay.addSpacing(4)
        lay.addWidget(self._sep())

        lay.addWidget(self._sb("⚙", "outils", self.tools_toggled))
        lay.addWidget(self._sb("↺", "hist.",  self.history_clicked))
        lay.addWidget(self._sb("◎", "mém.",   self.memory_clicked))
        lay.addWidget(self._sb("⊕", "fich.",  self.files_clicked))

        lay.addStretch()
        lay.addWidget(self._sep())
        lay.addWidget(self._sb("≡", "cfg.", self.settings_clicked))

        avatar = QLabel("AD")
        avatar.setFixedSize(28, 28)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(f"background:{GOLD_DIM}; color:{BG}; border-radius:14px; "
                             f"font-family:'{FONT_MONO}'; font-size:8pt; font-weight:bold;")
        wrap = QHBoxLayout()
        wrap.addStretch()
        wrap.addWidget(avatar)
        wrap.addStretch()
        lay.addSpacing(8)
        lay.addLayout(wrap)

    def _sep(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.NoFrame)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{BORDER}; border:none;")
        return line

    def _sb(self, icon, label, signal):
        b = QPushButton(f"{icon}\n{label}")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFixedHeight(46)
        b.setStyleSheet(f"""
            QPushButton {{
                color:{TEXT3}; background:{BG2}; border:none; border-radius:5px;
                font-family:'{FONT_MONO}'; font-size:7.5pt;
            }}
            QPushButton:hover {{ background:{BG4}; color:{GOLD}; }}
        """)
        b.clicked.connect(signal.emit)
        return b


# ═════════════════════════════════════════════════════════════════════════════
# Main widget — assemble topbar / chat / suggestions / input + panneau overlay
# ═════════════════════════════════════════════════════════════════════════════
class MainWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.topbar      = TopBar()
        self.chat        = ChatWidget()
        self.suggestions = SuggestionsBar()
        self.input_bar   = InputBar()

        lay.addWidget(self.topbar)
        lay.addWidget(self.chat, 1)
        lay.addWidget(self.suggestions)
        lay.addWidget(self.input_bar)

        self.tools_panel = ToolsPanel(self)


# ═════════════════════════════════════════════════════════════════════════════
# Fenêtre principale
# ═════════════════════════════════════════════════════════════════════════════
class AMAHWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Amah — Agent Local")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 640)
        self.setStyleSheet(f"background:{BG};")

        central = QWidget()
        central.setStyleSheet(f"background:{BG};")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = SidebarWidget()
        self.main    = MainWidget()
        root.addWidget(self.sidebar)
        root.addWidget(self.main, 1)
        self.setCentralWidget(central)

        self._busy   = False
        self._worker = None
        try:
            self.engine = ChatEngine()
        except Exception as e:
            self.main.chat.add_system_line(f"Erreur de demarrage : {e}", color=RED)
            self.engine = None

        self._wire_signals()
        self._welcome()

    # ── connexions ───────────────────────────────────────────────────────
    def _wire_signals(self):
        m = self.main
        self.sidebar.tools_toggled.connect(m.tools_panel.toggle)
        m.tools_panel.tool_selected.connect(self._on_tool_selected)
        m.suggestions.suggestion_clicked.connect(self._send_text)
        m.input_bar.message_sent.connect(self._send_text)
        m.topbar.actions.reset_clicked.connect(self._reset)
        m.topbar.actions.copy_clicked.connect(self._copy_last)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        panel = self.main.tools_panel
        if panel.isVisible():
            panel.setGeometry(self.main.width() - panel.width(), panel._panel_y(),
                              panel.width(), panel._panel_height(self.main))

    # ── comportement ─────────────────────────────────────────────────────
    def _welcome(self):
        self.main.chat.add_system_line(
            "Amah est prête. Pose ta question ou choisis une suggestion ci-dessous.", color=TEXT3)

    def _on_tool_selected(self, name: str):
        self.main.chat.add_system_line(f"⚙ Outil sélectionné : {name}", color=TEXT_TOOL)

    def _send_text(self, text: str):
        if self._busy or not text.strip() or self.engine is None:
            return
        self._busy = True
        self._last_reply = ""
        self.main.input_bar.set_busy(True)
        self.main.topbar.set_status("Amah reflechit...", "THINKING")

        self.main.chat.add_user_message(text)
        self.main.chat.start_amah_message()

        self._worker = ChatWorker(self.engine, text)
        self._worker.engine.thinking.connect(lambda s: self.main.topbar.set_status(s, "THINKING"))
        self._worker.engine.tool_used.connect(self._on_tool_used)
        self._worker.engine.reply_ready.connect(self._on_reply_ready)
        self._worker.engine.error_raised.connect(self._on_error)
        self._worker.start()

    def _on_tool_used(self, label: str):
        pass  # affiché en bloc à la fin de la réponse (pastilles)

    def _on_reply_ready(self, reply: str):
        self._last_reply = reply
        tools = list(self.engine._tools_this_call) if self.engine else []
        self.main.chat.end_amah_message(reply, tools)
        self._finish_turn(ok=True)

    def _on_error(self, message: str):
        self.main.chat.add_system_line(f"Erreur : {message}", color=RED)
        self._finish_turn(ok=False)

    def _finish_turn(self, ok: bool):
        self._busy = False
        self.main.input_bar.set_busy(False)
        state  = "IDLE" if ok else "ERROR"
        status = "AMAH // PRET" if ok else "AMAH // ERREUR"
        self.main.topbar.set_status(status, state)

    def _reset(self):
        if self.engine:
            self.engine.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            self.engine.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.main.chat.clear()
        self._welcome()
        self.main.topbar.set_status("AMAH // PRET", "IDLE")

    def _copy_last(self):
        if getattr(self, "_last_reply", ""):
            QApplication.clipboard().setText(self._last_reply)


# ─────────────────────────────────────────────────────────────────────────────
# Feuille de style globale (scrollbars, tooltips, menus)
# ─────────────────────────────────────────────────────────────────────────────
GLOBAL_QSS = f"""
QToolTip {{
    background: {BG2}; color: {TEXT}; border: 1px solid {BORDER2};
    padding: 4px 8px; font-family: '{FONT_MONO}'; font-size: 8pt;
}}
QMenu {{
    background: {BG2}; color: {TEXT}; border: 1px solid {BORDER2};
    font-family: '{FONT_MONO}'; font-size: 9pt;
}}
QMenu::item:selected {{ background: {GOLD_FAINT}; color: {GOLD}; }}
QScrollBar:vertical {{
    background: {BG}; width: 10px; margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER2}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {GOLD_DIM}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar:horizontal {{ height: 0px; }}
"""


def main():
    _load_fonts()
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_QSS)

    base_font = QFont(FONT_UI, 10)
    app.setFont(base_font)

    win = AMAHWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
