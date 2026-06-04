import os
import sys
import json
import time
import threading
import traceback
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS
from tools import TOOL_FUNCTIONS
from tools.memory import save_message, load_recent_messages, cleanup_old_messages, truncate_old_tool_results

# ── Couleurs ────────────────────────────────────────────────────────────────
BG_DARK    = "#1a1a17"
BG_PANEL   = "#222220"
BG_INPUT   = "#252522"
GOLD       = "#c8a96e"
GOLD_DIM   = "#7a5f38"
GOLD_LIGHT = "#d4b97e"
TEXT_WHITE = "#e8e0d0"
TEXT_DIM   = "#88887a"
TEXT_TOOL  = "#9a7a45"
RED        = "#c0392b"
GREEN      = "#27ae60"

MAX_MESSAGES = 16

TOOL_LABELS = {
    "list_files":      "lecture dossier",
    "organize_folder": "organisation",
    "find_files":      "recherche fichier",
    "move_file":       "deplacement",
    "create_folder":   "creation dossier",
    "read_file":       "lecture fichier",
    "get_folder_info": "infos dossier",
    "create_word":     "creation Word",
    "create_txt":      "creation TXT",
    "create_pdf":      "creation PDF",
    "read_document":   "lecture document",
    "web_search":      "recherche web",
    "read_webpage":    "lecture page",
    "get_system_info": "infos systeme",
    "open_file":       "ouverture fichier",
    "run_command":     "commande PowerShell",
    "save_memory":     "memorisation",
    "get_memories":    "rappel memoire",
    "delete_memory":   "suppression memoire",
    "read_emails":     "lecture emails",
    "send_email":      "envoi email",
    "search_emails":   "recherche emails",
    "open_browser":      "navigation web",
    "click_element":     "clic element",
    "fill_form":         "formulaire",
    "take_screenshot":   "capture ecran",
    "get_page_text":     "lecture page web",
    "speak":             "synthese vocale",
    "send_notification": "notification",
    "set_reminder":      "rappel programme",
    "read_excel":        "lecture Excel",
    "create_excel":      "creation Excel",
    "append_to_excel":   "ajout Excel",
}


class AmahGUI:
    def __init__(self, root):
        self.root       = root
        self.root.title("The Amah — Agent Local")
        self.root.configure(bg=BG_DARK)
        self.root.geometry("960x700")
        self.root.minsize(720, 520)

        # Rotation de clés API — charge toutes les clés disponibles
        self._api_keys = [k for k in [
            os.getenv("GROQ_API_KEY"),
            os.getenv("GROQ_API_KEY_2"),
            os.getenv("GROQ_API_KEY_3"),
        ] if k and not k.startswith("AJOUTER")]

        if not self._api_keys:
            messagebox.showerror("Cle manquante",
                "GROQ_API_KEY introuvable dans le fichier .env")
            sys.exit(1)

        self._key_index = 0
        self.client     = Groq(api_key=self._api_keys[0])
        self.session_id     = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.busy           = False
        self._last_reply    = ""
        self._tools_this_call = []   # outils utilisés dans l'appel en cours

        cleanup_old_messages(days=90)          # purge messages > 90 jours
        truncate_old_tool_results(max_chars=800)  # tronque tool_results longs en DB
        previous             = load_recent_messages(limit=10)  # 10 suffisent
        self.messages        = [{"role": "system", "content": SYSTEM_PROMPT}] + previous
        self._previous_count = len(previous)

        self._build_ui()
        self._bind_shortcuts()
        self._welcome()

    # ── Construction de l'interface ─────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        tk.Frame(self.root, bg=GOLD_DIM, height=1).pack(fill=tk.X)
        self._build_chat()
        tk.Frame(self.root, bg=GOLD_DIM, height=1).pack(fill=tk.X)
        self._build_input()
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG_PANEL, pady=10)
        hdr.pack(fill=tk.X)

        # Boutons à droite
        btn_frame = tk.Frame(hdr, bg=BG_PANEL)
        btn_frame.pack(side=tk.RIGHT, padx=14)

        tk.Button(btn_frame, text="Copier", bg="#2a2a27", fg=TEXT_DIM,
                  font=("Consolas", 9), relief=tk.FLAT, padx=10, pady=3,
                  cursor="hand2", command=self._copy_last).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(btn_frame, text="Reinitialiser", bg="#2a2a27", fg=GOLD_DIM,
                  font=("Consolas", 9), relief=tk.FLAT, padx=10, pady=3,
                  cursor="hand2", command=self._reset).pack(side=tk.LEFT)

        # Titre
        center = tk.Frame(hdr, bg=BG_PANEL)
        center.pack(expand=True)
        tk.Label(center, text="THE AMAH - AGENT LOCAL",
                 bg=BG_PANEL, fg=GOLD, font=("Consolas", 13, "bold")).pack()
        tk.Label(center, text="v1.3  ·  Groq  ·  65 outils  ·  Windows 11",
                 bg=BG_PANEL, fg=TEXT_DIM, font=("Consolas", 9)).pack()

    def _build_chat(self):
        self.chat = scrolledtext.ScrolledText(
            self.root, bg=BG_DARK, fg=TEXT_WHITE,
            font=("Consolas", 11), wrap=tk.WORD,
            state=tk.DISABLED, relief=tk.FLAT,
            padx=18, pady=14,
        )
        self.chat.pack(fill=tk.BOTH, expand=True)

        # Tags de style
        self.chat.tag_configure("amah_lbl",   foreground=GOLD,       font=("Consolas", 11, "bold"))
        self.chat.tag_configure("amah_txt",   foreground=TEXT_WHITE,  font=("Consolas", 11))
        self.chat.tag_configure("user_lbl",   foreground=TEXT_DIM,    font=("Consolas", 11))
        self.chat.tag_configure("user_txt",   foreground=TEXT_WHITE,  font=("Consolas", 11))
        self.chat.tag_configure("dim",        foreground=GOLD_DIM,    font=("Consolas", 10))
        self.chat.tag_configure("thinking",   foreground=GOLD_DIM,    font=("Consolas", 11, "italic"))
        self.chat.tag_configure("tool",       foreground=TEXT_TOOL,   font=("Consolas", 10, "italic"))
        self.chat.tag_configure("timestamp",  foreground="#4a4a42",   font=("Consolas", 9))
        self.chat.tag_configure("error",      foreground=RED,         font=("Consolas", 10))
        self.chat.tag_configure("separator",  foreground="#2a2a27",   font=("Consolas", 8))

        # Menu clic-droit
        self._ctx_menu = tk.Menu(self.root, tearoff=0, bg=BG_PANEL,
                                  fg=TEXT_WHITE, activebackground=GOLD_DIM)
        self._ctx_menu.add_command(label="Copier la derniere reponse", command=self._copy_last)
        self._ctx_menu.add_command(label="Tout selectionner", command=self._select_all)
        self.chat.bind("<Button-3>", self._show_ctx_menu)

    def _build_input(self):
        bar = tk.Frame(self.root, bg=BG_INPUT, pady=8)
        bar.pack(fill=tk.X)

        tk.Label(bar, text="Toi", bg=BG_INPUT, fg=TEXT_DIM,
                 font=("Consolas", 10)).pack(side=tk.LEFT, padx=(14, 6))
        tk.Label(bar, text=">", bg=BG_INPUT, fg=GOLD_DIM,
                 font=("Consolas", 11, "bold")).pack(side=tk.LEFT, padx=(0, 8))

        self.entry = tk.Text(bar, height=1,
                             bg="#2a2a27", fg=TEXT_WHITE,
                             insertbackground=GOLD,
                             font=("Consolas", 11),
                             relief=tk.FLAT, bd=0,
                             wrap=tk.WORD)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=2)

        self.btn = tk.Button(bar, text="Envoyer", bg=GOLD_DIM, fg=BG_DARK,
                             font=("Consolas", 10, "bold"), relief=tk.FLAT,
                             padx=14, pady=4, cursor="hand2", command=self._send)
        self.btn.pack(side=tk.LEFT, padx=(8, 14))

        self.entry.bind("<Return>",       self._on_return)
        self.entry.bind("<KeyRelease>",   self._resize_entry)
        self.entry.focus()

    def _build_statusbar(self):
        self._status_var = tk.StringVar(value="Pret")
        sb = tk.Frame(self.root, bg=BG_PANEL, pady=4)
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(sb, textvariable=self._status_var, bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Consolas", 9), anchor="w").pack(side=tk.LEFT, padx=14)
        tk.Label(sb, text="Shift+Entree = retour a la ligne  |  Ctrl+R = reinitialiser  |  Ctrl+C = copier",
                 bg=BG_PANEL, fg="#3a3a35",
                 font=("Consolas", 8), anchor="e").pack(side=tk.RIGHT, padx=14)

    def _bind_shortcuts(self):
        self.root.bind("<Control-r>", lambda e: self._reset())
        self.root.bind("<Control-R>", lambda e: self._reset())
        # Ctrl+C retiré du root — conflit avec la sélection de texte normale
        self.root.bind("<Escape>",    lambda e: self._clear_entry())

    # ── Saisie ──────────────────────────────────────────────────────────────

    def _on_return(self, event):
        if not event.state & 0x1:  # Shift non enfonce
            self._send()
            return "break"

    def _resize_entry(self, event=None):
        content = self.entry.get("1.0", tk.END)
        lines   = content.count("\n")
        self.entry.config(height=max(1, min(lines, 4)))

    def _clear_entry(self):
        self.entry.delete("1.0", tk.END)
        self.entry.config(height=1)

    # ── Ecriture dans le chat ────────────────────────────────────────────────

    def _ts(self):
        return datetime.now().strftime("%H:%M")

    def _write(self, *parts):
        self.chat.config(state=tk.NORMAL)
        for text, tag in parts:
            self.chat.insert(tk.END, text, tag)
        self.chat.config(state=tk.DISABLED)
        self.chat.see(tk.END)

    def _write_msg(self, who, text, lbl_tag, txt_tag):
        ts = self._ts()
        self._write(
            (f"[{ts}] ", "timestamp"),
            (f"{who} ", lbl_tag),
            (text + "\n\n", txt_tag),
        )

    def _write_tool(self, tool_name):
        label = TOOL_LABELS.get(tool_name, tool_name)
        self._write((f"        outil : {label}\n", "tool"))

    def _write_separator(self):
        self._write(("  " + "-" * 60 + "\n", "separator"))

    # ── Messages de l'interface ──────────────────────────────────────────────

    def _welcome(self):
        if self._previous_count > 0:
            self._write((f"  {self._previous_count} messages de la session precedente charges.\n\n", "dim"))
        self._write_msg("Amah >", "Tu m'as trouvee. Qu'est-ce que tu veux faire ?", "amah_lbl", "amah_txt")
        self._write(("  Shift+Entree = retour a la ligne  |  'outils' = liste des outils\n\n", "dim"))
        self._set_status("Pret")

    def _set_status(self, text, color=None):
        self._status_var.set(text)

    # ── Envoi et traitement ──────────────────────────────────────────────────

    def _send(self, event=None):
        if self.busy:
            return
        text = self.entry.get("1.0", tk.END).strip()
        if not text:
            return
        self._clear_entry()

        if text.lower() in ["quitter", "exit", "quit"]:
            self.root.quit()
            return

        if text.lower() == "reset":
            self._reset()
            return

        if text.lower() == "outils":
            self._write_msg("Toi  >", text, "user_lbl", "user_txt")
            self._show_tools()
            return

        self._write_msg("Toi  >", text, "user_lbl", "user_txt")
        self.messages.append({"role": "user", "content": text})
        save_message(self.session_id, "user", text)

        self.chat.config(state=tk.NORMAL)
        self.chat.mark_set("thinking_start", tk.END)
        self.chat.mark_gravity("thinking_start", tk.LEFT)
        self.chat.config(state=tk.DISABLED)
        self._write((f"[{self._ts()}] ", "timestamp"),
                    ("Amah > ", "amah_lbl"),
                    ("reflechit...\n\n", "thinking"))

        self.busy = True
        self._tools_this_call = []   # remet à zéro pour ce nouvel appel
        self.entry.config(state=tk.DISABLED)
        self.btn.config(state=tk.DISABLED)
        self._set_status("Amah reflechit...")
        threading.Thread(target=self._run_chat, daemon=True).start()

    def _run_chat(self):
        try:
            reply = self._chat()
            self.messages.append({"role": "assistant", "content": reply})
            save_message(self.session_id, "assistant", reply)
            self.root.after(0, self._show_reply, reply)
        except Exception as e:
            self.root.after(0, self._show_error, self._format_error(str(e)))

    def _format_error(self, error: str) -> str:
        if "rate_limit_exceeded" in error or "Rate limit" in error:
            import re
            wait = re.search(r"try again in (.+?)\.", error)
            temps = wait.group(1) if wait else "quelques minutes"
            return (
                f"Limite quotidienne Groq atteinte.\n"
                f"Attends {temps} avant de continuer.\n"
                f"Ou cree un 2eme compte gratuit sur console.groq.com"
            )
        if "invalid_api_key" in error or "API key" in error.lower():
            return "Cle API Groq invalide. Verifie ta cle dans le fichier .env"
        if "connection" in error.lower() or "network" in error.lower():
            return "Pas de connexion internet. Verifie ta connexion et reessaie."
        if "timeout" in error.lower():
            return "La requete a pris trop de temps. Reessaie dans un moment."
        return error

    def _show_reply(self, reply):
        self._last_reply = reply
        # Supprime uniquement le "réfléchit..." — pas les outils déjà affichés
        self.chat.config(state=tk.NORMAL)
        self.chat.delete("thinking_start", tk.END)
        self.chat.config(state=tk.DISABLED)
        # Affiche les outils utilisés pendant cet appel
        if self._tools_this_call:
            outils = " → ".join(self._tools_this_call)
            self._write((f"  [ {outils} ]\n", "tool"))
        self._tools_this_call = []
        self._write((f"[{self._ts()}] ", "timestamp"),
                    ("Amah > ", "amah_lbl"),
                    (reply + "\n\n", "amah_txt"))
        self._write_separator()
        self._unlock()
        self._set_status("Pret")

    def _show_error(self, error):
        self.chat.config(state=tk.NORMAL)
        self.chat.delete("thinking_start", tk.END)
        self.chat.config(state=tk.DISABLED)
        self._write((f"  Erreur : {error}\n\n", "error"))
        self._unlock()
        self._set_status("Erreur")

    def _unlock(self):
        self.busy = False
        self.entry.config(state=tk.NORMAL)
        self.btn.config(state=tk.NORMAL)
        self.entry.focus()

    # ── Actions ──────────────────────────────────────────────────────────────

    def _reset(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._write(("\n  --- Conversation reinitialisee ---\n\n", "dim"))
        self._set_status("Pret")

    def _copy_last(self):
        # Lit directement le dernier message Amah dans le chat (plus fiable)
        content = self.chat.get("1.0", tk.END)
        marker  = "Amah > "
        last_idx = content.rfind(marker)
        if last_idx != -1:
            after   = content[last_idx + len(marker):]
            sep_idx = after.find("-" * 30)
            text    = after[:sep_idx].strip() if sep_idx != -1 else after.strip()
        elif self._last_reply:
            text = self._last_reply
        else:
            return
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._set_status("Derniere reponse copiee !")
            self.root.after(2000, lambda: self._set_status("Pret"))

    def _select_all(self):
        self.chat.config(state=tk.NORMAL)
        self.chat.tag_add(tk.SEL, "1.0", tk.END)
        self.chat.config(state=tk.DISABLED)

    def _show_ctx_menu(self, event):
        self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _show_tools(self):
        cats = {
            "Fichiers":   ["list_files", "organize_folder", "find_files", "move_file",
                           "create_folder", "read_file", "get_folder_info"],
            "Documents":  ["create_word", "create_txt", "create_pdf", "read_document"],
            "Internet":   ["web_search", "read_webpage"],
            "Systeme":    ["get_system_info", "open_file", "run_command"],
            "Memoire":    ["save_memory", "get_memories", "delete_memory"],
            "Email":      ["read_emails", "send_email", "search_emails"],
            "Navigateur": ["open_browser", "click_element", "fill_form",
                           "take_screenshot", "get_page_text"],
        }
        self._write(("\n", "dim"))
        for cat, tools in cats.items():
            self._write((f"  {cat}: ", "amah_lbl"),
                        (" · ".join(tools) + "\n", "dim"))
        self._write(("\n", "dim"))

    # ── Moteur de chat ────────────────────────────────────────────────────────

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

        # Collecte le nom (affiché après la réponse, pas pendant — évite la suppression)
        self._tools_this_call.append(TOOL_LABELS.get(name, name))
        label = TOOL_LABELS.get(name, name)
        self.root.after(0, self._set_status, f"Outil : {label}...")

        try:
            result = func(**args)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    # Mots clés → catégorie d'outils (élargi pour couvrir un maximum de cas)
    _WORD_TO_CAT = {
        # fichiers
        "liste":"fichiers","lister":"fichiers","fichier":"fichiers","fichiers":"fichiers",
        "dossier":"fichiers","dossiers":"fichiers","trouve":"fichiers","trouver":"fichiers",
        "deplace":"fichiers","organise":"fichiers","organiser":"fichiers","classe":"fichiers",
        "lis":"fichiers","lire":"fichiers","lit":"fichiers","affiche":"fichiers",
        "montre":"fichiers","montre-moi":"fichiers","montrer":"fichiers","vois":"fichiers",
        "find":"fichiers","read":"fichiers","bureau":"fichiers","desktop":"fichiers",
        "downloads":"fichiers","telechargements":"fichiers","taille":"fichiers",
        "renomme":"fichiers","supprime":"fichiers","copie":"fichiers",
        # extensions de fichiers → toujours catégorie fichiers
        "html":"fichiers","htm":"fichiers","index":"fichiers","css":"fichiers",
        "js":"fichiers","py":"fichiers","json":"fichiers","xml":"fichiers",
        "csv":"fichiers","log":"fichiers","ini":"fichiers","cfg":"fichiers",
        "exe":"fichiers","bat":"fichiers","sh":"fichiers","md":"fichiers",
        # documents
        "word":"documents","pdf":"documents","txt":"documents","document":"documents",
        "rapport":"documents","cree":"documents","creer":"documents","genere":"documents",
        "generer":"documents","redige":"documents","rediger":"documents","ecrit":"documents",
        "ecrire":"documents","fais":"documents","faire":"documents","prepare":"documents",
        "write":"documents","create":"documents","make":"documents","resume":"documents",
        "synthese":"documents","lettre":"documents","contrat":"documents","facture":"documents",
        # internet / navigateur
        "web":"internet","recherche":"internet","rechercher":"internet","site":"internet",
        "navigateur":"internet","ouvre":"internet","ouvrir":"internet","visite":"internet",
        "cherche":"internet","chercher":"internet","url":"internet","open":"internet",
        "click":"internet","clique":"internet","screenshot":"internet","capture":"internet",
        "telecharge":"internet","linkedin":"internet","google":"internet","youtube":"internet",
        "instagram":"internet","navigue":"internet","va":"internet","vas":"internet",
        "page":"internet","contenu":"internet","lis-la":"internet","scrape":"internet",
        # email
        "email":"email","emails":"email","mail":"email","mails":"email","boite":"email",
        "envoie":"email","envoyer":"email","lis-mes":"email","dernier-email":"email",
        "send":"email","gmail":"email","message":"email","reponse":"email","repond":"email",
        "expediteur":"email","sujet":"email","piece":"email","jointe":"email",
        "inbox":"email","reception":"email","nouveau":"email","nouveaux":"email",
        "recus":"email","recu":"email","non-lu":"email","nonlu":"email",
        "messagerie":"email","courrier":"email","courriel":"email",
        # mémoire
        "memorise":"memoire","souviens":"memoire","rappelle":"memoire","memoire":"memoire",
        "retiens":"memoire","note":"memoire","notes":"memoire","oublie":"memoire",
        "sais":"memoire","sait":"memoire","preference":"memoire","info":"memoire",
        # système
        "systeme":"systeme","processus":"systeme","process":"systeme","reseau":"systeme",
        "ip":"systeme","commande":"systeme","run":"systeme","execute":"systeme",
        "lance":"systeme","ferme":"systeme","ram":"systeme","cpu":"systeme",
        "disque":"systeme","windows":"systeme","pc":"systeme","ordinateur":"systeme",
        # utilitaires / calcul
        "calcule":"utils","calculer":"utils","convertis":"utils","convertir":"utils",
        "date":"utils","heure":"utils","password":"utils","passe":"utils","genere":"utils",
        "zip":"utils","archive":"utils","qr":"utils","code":"utils","qrcode":"utils",
        "combien":"utils","quel":"utils","quand":"utils","dans":"utils","depuis":"utils",
        "ajoute":"utils","ajouter":"utils","jours":"utils","mois":"utils","annee":"utils",
        # data (Excel, presse-papiers)
        "excel":"data","tableau":"data","tableur":"data","xlsx":"data","csv":"data",
        "clipboard":"data","presse-papiers":"data","copier":"data","coller":"data",
        "contenu-presse":"data","presse":"data",
        # médias / voix
        "parle":"media","dis":"media","dis-moi":"media","voix":"media","speak":"media",
        "ecoute":"media","microphone":"media","micro":"media","notification":"media",
        "notifie":"media","alerte":"media","rappel":"media","rappelle-moi":"media",
        "dans-x-minutes":"media","dans-x-heures":"media","bip":"media",
        "screenshot-ecran":"media","capture-ecran":"media","ecran":"media",
        # images
        "image":"images","images":"images","photo":"images","photos":"images",
        "redimensionne":"images","resize":"images","convertis-image":"images",
        "png":"images","jpg":"images","jpeg":"images","webp":"images","bmp":"images",
        # météo / info / traduction
        "meteo":"info","temps":"info","temperature":"info","previsions":"info",
        "traduis":"info","traduire":"info","traduction":"info","langue":"info",
        "translate":"info","stats":"info","statistiques":"info","version":"info",
        "licence":"info","mise-a-jour":"info","update":"info","pluie":"info","soleil":"info",
        # planificateur
        "planifie":"planif","planifier":"planif","tache":"planif","taches":"planif",
        "planificateur":"planif","cron":"planif","automatique":"planif","chaque":"planif",
        "quotidien":"planif","hebdo":"planif","programme":"planif",
    }

    # Catégories → noms d'outils inclus
    _CAT_TOOLS = {
        "fichiers":  {"list_files","organize_folder","find_files","move_file","create_folder","read_file","get_folder_info"},
        "documents": {"create_word","create_txt","create_pdf","read_document"},
        "internet":  {"web_search","read_webpage","open_browser","click_element","fill_form","take_screenshot","get_page_text"},
        "email":     {"read_emails","send_email","search_emails"},
        "memoire":   {"save_memory","get_memories","delete_memory"},
        "systeme":   {"get_system_info","open_file","run_command","list_processes","get_network_info"},
        "utils":     {"calculate","get_datetime","add_days","generate_password","convert_units","zip_files","unzip_file","list_archive","create_qrcode"},
        "data":      {"read_excel","create_excel","append_to_excel","read_clipboard","write_clipboard"},
        "media":     {"speak","listen","listen_continuous","send_notification","set_reminder","screenshot_full"},
        "images":    {"resize_image","get_image_info","convert_image"},
        "info":      {"get_weather","get_weather_simple","translate","detect_language","get_stats","check_update","get_current_version","get_license_info"},
        "planif":    {"create_daily_task","list_tasks","delete_task","run_task_now"},
    }

    def _select_tools(self, message: str):
        """Retourne la sous-liste TOOLS_DEFINITIONS pertinente, ou None si pas d'outil."""
        words = message.lower().replace("'", " ").split()
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
        """Garde system prompt + MAX_MESSAGES derniers messages.
        Préserve les paires tool_call/tool_result pour éviter les erreurs API."""
        if len(self.messages) <= MAX_MESSAGES + 1:
            return
        system  = self.messages[0]
        tail    = self.messages[-MAX_MESSAGES:]
        # S'assurer qu'on ne coupe pas une paire tool_call orpheline
        while tail and tail[0].get("role") == "tool":
            tail = tail[1:]
        self.messages = [system] + tail

    def _next_key(self):
        """Bascule vers la clé API suivante disponible."""
        nb = len(self._api_keys)
        if nb <= 1:
            return False
        self._key_index = (self._key_index + 1) % nb
        self.client = Groq(api_key=self._api_keys[self._key_index])
        return True

    def _groq_call(self, messages, tools=None, model_override=None):
        """Appel Groq avec rotation de clés + retry backoff (1s, 2s, 4s).
        model_override : force un modèle spécifique (ex: 8B pour questions simples)
        """
        used_model = model_override or MODEL
        kwargs = dict(model=used_model, messages=messages, max_tokens=1024, temperature=0.4)
        if tools:
            kwargs["tools"] = tools; kwargs["tool_choice"] = "auto"

        keys_tried = 0
        delays     = [1, 2, 4]

        for attempt in range(len(delays) * len(self._api_keys)):
            try:
                return self.client.chat.completions.create(**kwargs)
            except Exception as e:
                err = str(e)
                is_limit = "429" in err or "rate_limit" in err or "TPD" in err or "TPM" in err

                if is_limit:
                    # Essaie d'abord de changer de clé
                    if keys_tried < len(self._api_keys) - 1 and self._next_key():
                        keys_tried += 1
                        nb_keys = len(self._api_keys)
                        idx     = self._key_index + 1
                        self.root.after(0, self._set_status,
                            f"Cle {idx}/{nb_keys} — limite atteinte, rotation...")
                        continue
                    # Plus de clé dispo → attente backoff
                    delay = delays[min(attempt, len(delays)-1)]
                    self.root.after(0, self._set_status,
                        f"Toutes les cles limitees — attente {delay}s...")
                    time.sleep(delay)
                elif "503" in err:
                    delay = delays[min(attempt, len(delays)-1)]
                    time.sleep(delay)
                else:
                    raise

    def _chat(self) -> str:
        self._trim_messages()

        # Sélection ciblée des outils : envoie uniquement la catégorie pertinente
        last_user = next(
            (m["content"] for m in reversed(self.messages) if m["role"] == "user"), ""
        )
        tools = self._select_tools(last_user)

        # ── Sélection du modèle selon la complexité ───────────────────────────
        # Questions simples (salutation, calcul rapide, date...) → 8B instant
        # Tâches avec outils → 70B versatile (qualité + tool use)
        SIMPLE_PATTERNS = {
            "bonjour","bonsoir","salut","hello","hi","merci","ok","oui","non",
            "comment","quoi","qui","quand","pourquoi","combien","cest","cest-quoi",
            "explique","dis","repete","aide","help","test","essai",
        }
        words_lower = set(last_user.lower().replace("'", " ").split())
        is_simple   = (len(last_user.split()) <= 6 and
                       bool(words_lower & SIMPLE_PATTERNS) and
                       not tools)

        if is_simple:
            active_model = "llama-3.1-8b-instant"
            self.root.after(0, self._set_status, "Amah reflechit...")
        elif not tools:
            active_model = MODEL
            DEFAULT_TOOLS = {
                "web_search","read_webpage","list_files","read_file",
                "create_word","get_datetime","calculate",
                "save_memory","get_memories","read_emails",
                "send_email","get_system_info","speak",
            }
            tools = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] in DEFAULT_TOOLS]
            self.root.after(0, self._set_status, "Amah reflechit...")
        else:
            active_model = MODEL
            self.root.after(0, self._set_status, "Amah reflechit (outils cibles)...")

        response = self._groq_call(self.messages, tools=tools, model_override=active_model)

        # Si le modèle réclame un outil hors de la sous-liste → relancer avec tous (70B)
        if response.choices[0].finish_reason == "tool_calls":
            tool_names = {tc.function.name for tc in (response.choices[0].message.tool_calls or [])}
            available  = {t["function"]["name"] for t in (tools or [])}
            if not tool_names.issubset(available):
                response = self._groq_call(self.messages, tools=TOOLS_DEFINITIONS,
                                           model_override=MODEL)

        while response.choices[0].finish_reason == "tool_calls":
            msg = response.choices[0].message
            if not msg.tool_calls:
                break

            msg_dict = {
                "role":    "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            }
            self.messages.append(msg_dict)

            for tc in msg.tool_calls:
                result = self._execute_tool(tc)
                # Tronque les résultats trop longs pour économiser les tokens
                # (emails, fichiers, pages web peuvent faire des milliers de tokens)
                if len(result) > 2000:
                    result = result[:2000] + "\n...[tronqué pour économiser les tokens]"
                self.messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      result,
                })

            self._trim_messages()
            response = self._groq_call(self.messages, tools=TOOLS_DEFINITIONS,
                                       model_override=MODEL)  # toujours 70B pour tool use

        return response.choices[0].message.content


# ── Écran de configuration (premier lancement) ──────────────────────────────

class SetupWindow:
    def __init__(self, root, on_complete, env_path):
        self.root        = root
        self.on_complete = on_complete
        self.env_path    = env_path

        self.root.title("Amah Agent — Configuration")
        self.root.configure(bg=BG_DARK)
        self.root.geometry("660x680")
        self.root.resizable(False, False)
        self._build()

    def _build(self):
        hdr = tk.Frame(self.root, bg=BG_PANEL, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="THE AMAH — PREMIER LANCEMENT",
                 bg=BG_PANEL, fg=GOLD, font=("Consolas", 13, "bold")).pack()
        tk.Label(hdr, text="Configure tes acces pour demarrer",
                 bg=BG_PANEL, fg=TEXT_DIM, font=("Consolas", 9)).pack()
        tk.Label(hdr, text="v1.3.0  ·  65 outils  ·  Windows 11",
                 bg=BG_PANEL, fg=GOLD_DIM, font=("Consolas", 8)).pack()
        tk.Frame(self.root, bg=GOLD_DIM, height=1).pack(fill=tk.X)

        # Scrollable si besoin
        body = tk.Frame(self.root, bg=BG_DARK, padx=28, pady=14)
        body.pack(fill=tk.BOTH, expand=True)

        # ── Section Groq ──────────────────────────────────────────────────────
        tk.Frame(body, bg=GOLD_DIM, height=1).pack(fill=tk.X, pady=(0, 10))

        # Bannière info clés multiples
        info = tk.Frame(body, bg="#1e1c10", pady=6, padx=10)
        info.pack(fill=tk.X, pady=(0, 10))
        tk.Label(info, text="3 cles = 3x plus d'appels par jour (gratuit)",
                 bg="#1e1c10", fg=GOLD, font=("Consolas", 9, "bold")).pack(anchor="w")
        tk.Label(info, text="Cree jusqu'a 3 comptes gratuits sur console.groq.com",
                 bg="#1e1c10", fg=TEXT_DIM, font=("Consolas", 9)).pack(anchor="w")

        self._lbl(body, "Cle Groq n1", "obligatoire · console.groq.com")
        self.v_groq1 = tk.StringVar()
        tk.Entry(body, textvariable=self.v_groq1, show="*", **self._es()).pack(fill=tk.X, pady=(0, 10))

        self._lbl(body, "Cle Groq n2", "optionnel · 2eme compte = +100 000 tokens/jour")
        self.v_groq2 = tk.StringVar()
        tk.Entry(body, textvariable=self.v_groq2, show="*", **self._es()).pack(fill=tk.X, pady=(0, 10))

        self._lbl(body, "Cle Groq n3", "optionnel · 3eme compte = +100 000 tokens/jour")
        self.v_groq3 = tk.StringVar()
        tk.Entry(body, textvariable=self.v_groq3, show="*", **self._es()).pack(fill=tk.X, pady=(0, 10))

        # ── Section Licence ───────────────────────────────────────────────────
        tk.Frame(body, bg=GOLD_DIM, height=1).pack(fill=tk.X, pady=(4, 10))

        self._lbl(body, "Cle de licence", "obligatoire · fournie par contact.amah.officiel@gmail.com")
        self.v_licence = tk.StringVar()
        lic_frame = tk.Frame(body, bg=BG_DARK)
        lic_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Entry(lic_frame, textvariable=self.v_licence,
                 bg="#2a2a27", fg=TEXT_WHITE, insertbackground=GOLD,
                 font=("Consolas", 11), relief=tk.FLAT, bd=4).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(lic_frame, text="UUID", bg="#2a2a27", fg=TEXT_DIM,
                  font=("Consolas", 9), relief=tk.FLAT, padx=8,
                  cursor="hand2", command=self._copy_uuid).pack(side=tk.LEFT, padx=(6, 0))

        # UUID machine (pour le client)
        from tools.license import get_machine_id as _gmid
        self._machine_id = _gmid()
        uuid_lbl = tk.Frame(body, bg="#1a1a10", pady=4, padx=8)
        uuid_lbl.pack(fill=tk.X, pady=(0, 10))
        tk.Label(uuid_lbl, text="Votre identifiant machine (a envoyer pour obtenir la cle) :",
                 bg="#1a1a10", fg=TEXT_DIM, font=("Consolas", 8)).pack(anchor="w")
        tk.Label(uuid_lbl, text=self._machine_id,
                 bg="#1a1a10", fg=GOLD, font=("Consolas", 10, "bold")).pack(anchor="w")

        # ── Section Gmail ─────────────────────────────────────────────────────
        tk.Frame(body, bg=GOLD_DIM, height=1).pack(fill=tk.X, pady=(4, 10))

        self._lbl(body, "Adresse Gmail", "optionnel · pour lire et envoyer des emails")
        self.v_gmail = tk.StringVar(value="contact.amah.officiel@gmail.com")
        tk.Entry(body, textvariable=self.v_gmail, **self._es()).pack(fill=tk.X, pady=(0, 10))

        self._lbl(body, "Mot de passe application Gmail",
                  "optionnel · Compte Google > Securite > Mots de passe des applications")
        self.v_pwd = tk.StringVar()
        tk.Entry(body, textvariable=self.v_pwd, show="*", **self._es()).pack(fill=tk.X, pady=(0, 14))

        # ── Erreur + bouton ───────────────────────────────────────────────────
        self.v_err = tk.StringVar()
        tk.Label(body, textvariable=self.v_err, bg=BG_DARK,
                 fg=RED, font=("Consolas", 10)).pack(pady=(0, 6))

        tk.Button(body, text="Demarrer Amah", bg=GOLD_DIM, fg=BG_DARK,
                  font=("Consolas", 11, "bold"), relief=tk.FLAT,
                  padx=20, pady=6, cursor="hand2", command=self._save).pack()

    def _lbl(self, parent, title, hint):
        tk.Label(parent, text=title, bg=BG_DARK, fg=GOLD,
                 font=("Consolas", 10, "bold"), anchor="w").pack(fill=tk.X)
        tk.Label(parent, text=hint, bg=BG_DARK, fg=TEXT_DIM,
                 font=("Consolas", 9), anchor="w").pack(fill=tk.X, pady=(0, 3))

    def _es(self):
        return dict(bg="#2a2a27", fg=TEXT_WHITE, insertbackground=GOLD,
                    font=("Consolas", 11), relief=tk.FLAT, bd=4)

    def _copy_uuid(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self._machine_id)

    def _save(self):
        from tools.license import validate_license
        groq1   = self.v_groq1.get().strip()
        groq2   = self.v_groq2.get().strip()
        groq3   = self.v_groq3.get().strip()
        licence = self.v_licence.get().strip()
        gmail   = self.v_gmail.get().strip()
        pwd     = self.v_pwd.get().strip()

        if not groq1:
            self.v_err.set("La cle Groq n1 est obligatoire.")
            return
        if not licence:
            self.v_err.set("La cle de licence est obligatoire.")
            return
        if not validate_license(licence):
            self.v_err.set("Cle de licence invalide. Contactez contact.amah.officiel@gmail.com")
            return

        lines = [f"GROQ_API_KEY={groq1}\n"]
        if groq2:   lines.append(f"GROQ_API_KEY_2={groq2}\n")
        if groq3:   lines.append(f"GROQ_API_KEY_3={groq3}\n")
        lines.append(f"AMAH_LICENSE_KEY={licence}\n")
        if gmail:   lines.append(f"GMAIL_ADDRESS={gmail}\n")
        if pwd:     lines.append(f"GMAIL_APP_PASSWORD={pwd}\n")

        self.env_path.write_text(''.join(lines), encoding='utf-8')
        load_dotenv(self.env_path, override=True)
        self.on_complete()


# ── Écran de licence obligatoire ────────────────────────────────────────────

class LicenseWindow:
    def __init__(self, root, on_complete, env_path):
        self.root        = root
        self.on_complete = on_complete
        self.env_path    = env_path

        from tools.license import get_machine_id
        self.machine_id = get_machine_id()

        self.root.title("Amah Agent — Activation requise")
        self.root.configure(bg=BG_DARK)
        self.root.geometry("640x440")
        self.root.resizable(False, False)
        self._build()

    def _build(self):
        # En-tête
        hdr = tk.Frame(self.root, bg=BG_PANEL, pady=14)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="THE AMAH — ACTIVATION",
                 bg=BG_PANEL, fg=GOLD, font=("Consolas", 13, "bold")).pack()
        tk.Label(hdr, text="Une cle de licence est requise pour utiliser Amah Agent",
                 bg=BG_PANEL, fg=TEXT_DIM, font=("Consolas", 9)).pack()
        tk.Label(hdr, text="v1.3.0  ·  65 outils  ·  Windows 11",
                 bg=BG_PANEL, fg=GOLD_DIM, font=("Consolas", 8)).pack()
        tk.Frame(self.root, bg=GOLD_DIM, height=1).pack(fill=tk.X)

        body = tk.Frame(self.root, bg=BG_DARK, padx=32, pady=18)
        body.pack(fill=tk.BOTH, expand=True)

        # Machine UUID — à envoyer au vendeur
        tk.Label(body, text="Votre identifiant machine (a envoyer a contact.amah.officiel@gmail.com) :",
                 bg=BG_DARK, fg=TEXT_DIM, font=("Consolas", 9), anchor="w").pack(fill=tk.X)

        uuid_frame = tk.Frame(body, bg="#2a2a27", pady=8)
        uuid_frame.pack(fill=tk.X, pady=(4, 14))
        tk.Label(uuid_frame, text=self.machine_id,
                 bg="#2a2a27", fg=GOLD, font=("Consolas", 11, "bold")).pack(side=tk.LEFT, padx=12)
        tk.Button(uuid_frame, text="Copier", bg=GOLD_DIM, fg=BG_DARK,
                  font=("Consolas", 9), relief=tk.FLAT, padx=8, pady=2,
                  cursor="hand2", command=self._copy_uuid).pack(side=tk.RIGHT, padx=8)

        # Clé de licence
        tk.Label(body, text="Cle de licence :",
                 bg=BG_DARK, fg=GOLD, font=("Consolas", 10, "bold"), anchor="w").pack(fill=tk.X)
        tk.Label(body, text="Format : XXXXX-XXXXX-XXXXX-XXXXX",
                 bg=BG_DARK, fg=TEXT_DIM, font=("Consolas", 9), anchor="w").pack(fill=tk.X, pady=(0, 4))

        self.v_key = tk.StringVar()
        tk.Entry(body, textvariable=self.v_key,
                 bg="#2a2a27", fg=TEXT_WHITE, insertbackground=GOLD,
                 font=("Consolas", 12), relief=tk.FLAT, bd=4).pack(fill=tk.X, pady=(0, 4))

        self.v_err = tk.StringVar()
        tk.Label(body, textvariable=self.v_err, bg=BG_DARK,
                 fg=RED, font=("Consolas", 10)).pack(pady=(4, 8))

        tk.Button(body, text="Activer Amah", bg=GOLD_DIM, fg=BG_DARK,
                  font=("Consolas", 11, "bold"), relief=tk.FLAT,
                  padx=20, pady=6, cursor="hand2", command=self._validate).pack()

        tk.Label(body,
                 text="Pour obtenir votre cle : contact.amah.officiel@gmail.com",
                 bg=BG_DARK, fg=TEXT_DIM, font=("Consolas", 9)).pack(pady=(14, 0))

    def _copy_uuid(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.machine_id)

    def _validate(self):
        from tools.license import validate_license
        key = self.v_key.get().strip()
        if not key:
            self.v_err.set("Veuillez entrer votre cle de licence.")
            return
        if not validate_license(key):
            self.v_err.set("Cle invalide. Verifiez la cle ou contactez le support.")
            return
        # Clé valide — sauvegarder dans .env
        content = self.env_path.read_text(encoding='utf-8') if self.env_path.exists() else ""
        if "AMAH_LICENSE_KEY" in content:
            import re
            content = re.sub(r"AMAH_LICENSE_KEY=.*", f"AMAH_LICENSE_KEY={key}", content)
        else:
            content += f"\nAMAH_LICENSE_KEY={key}\n"
        self.env_path.write_text(content, encoding='utf-8')
        load_dotenv(self.env_path, override=True)
        self.on_complete()


# ── Rapport de crash automatique ────────────────────────────────────────────

def _setup_crash_reporter():
    original = sys.excepthook

    def _handler(exc_type, exc_value, exc_tb):
        try:
            tb   = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            body = f"CRASH AMAH AGENT\n\n{tb}\n\nVersion: 1.0.0\nDate: {datetime.now()}"
            from tools.email_tool import send_email
            send_email("contact.amah.officiel@gmail.com", "Amah Agent — Crash rapport", body)
        except Exception:
            pass
        original(exc_type, exc_value, exc_tb)

    sys.excepthook = _handler


# ── Check Playwright ─────────────────────────────────────────────────────────

def _check_playwright() -> bool:
    """Vérifie si Chromium est installé — simple vérification de fichier, pas de lancement."""
    import glob
    pattern = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "ms-playwright", "chromium*", "chrome-win", "chrome.exe"
    )
    return bool(glob.glob(pattern))


# ── Point d'entrée ──────────────────────────────────────────────────────────

def main():
    _setup_crash_reporter()

    env_path = (Path(sys.executable).parent / '.env'
                if getattr(sys, 'frozen', False)
                else Path(__file__).parent / '.env')
    load_dotenv(env_path)

    # Avertissement Playwright non bloquant
    if not _check_playwright():
        print("[WARN] Chromium non installe — outils navigateur indisponibles")

    root = tk.Tk()

    def launch_amah():
        for w in root.winfo_children():
            w.destroy()
        root.geometry("960x700")
        root.resizable(True, True)
        AmahGUI(root)

    def check_license():
        from tools.license import is_licensed
        if not is_licensed():
            # Licence manquante → LicenseWindow de secours (si .env existe sans licence)
            LicenseWindow(root, launch_amah, env_path)
        else:
            launch_amah()

    if not os.getenv('GROQ_API_KEY'):
        # Premier lancement — tout dans SetupWindow (Groq + Licence + Gmail)
        def after_setup():
            for w in root.winfo_children():
                w.destroy()
            launch_amah()  # Licence déjà validée dans SetupWindow._save()
        SetupWindow(root, after_setup, env_path)
    else:
        # .env existe — vérifie la licence
        check_license()

    root.mainloop()


if __name__ == "__main__":
    main()
