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
from types import SimpleNamespace
from groq import Groq
from groq_client import GroqClient, repair_tool_use_failed
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS, chat_messages
from tools import TOOL_FUNCTIONS, resolve_tool_name
from tools.updater import CURRENT_VERSION
from tools.tool_router import select_tools, forced_tool
from tools.instant import instant_reply
from tools.memory_context import memory_context, memory_instruction, SUMMARY_SYSTEM as MEMORY_SUMMARY_SYSTEM
from tools.memory_recall_v024 import format_recall
from tools.guard import set_confirm_handler, tk_confirm_handler
from tools.memory import (save_message, load_resume_messages, cleanup_old_messages,
                          truncate_old_tool_results, history_retention_days)
from webcam_monitor import WebcamMonitor

# ── Couleurs ────────────────────────────────────────────────────────────────
BG         = "#0D0D0B"   # fond principal
BG2        = "#121210"   # sidebar, topbar
BG3        = "#181815"   # input, bulles
BG4        = "#1E1E1A"   # hover
BORDER     = "#2A2A22"   # bordures subtiles
BORDER2    = "#3A3A2E"   # bordures visibles
GOLD       = "#C8A96E"
GOLD2      = "#E8C98E"
GOLD_DIM   = "#7A5F38"
GOLD_FAINT = "#2A1F0A"
TEXT       = "#E8E0D0"
TEXT2      = "#9A9280"
TEXT3      = "#5A5448"
TEXT_TOOL  = "#9A7A45"
RED        = "#C0392B"
GREEN      = "#27AE60"
CYAN       = "#00D4FF"
# Aliases compat
BG_DARK = BG; BG_PANEL = BG2; BG_INPUT = BG3
TEXT_WHITE = TEXT; TEXT_DIM = TEXT2; GOLD_LIGHT = GOLD2

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
    "click_text":        "clic sur texte",
    "type_in_field":     "saisie champ",
    "speak":             "synthese vocale",
    "send_notification": "notification",
    "set_reminder":      "rappel programme",
    "read_excel":        "lecture Excel",
    "create_excel":      "creation Excel",
    "append_to_excel":   "ajout Excel",
    "write_file":        "ecriture fichier",
    "edit_file":         "edition fichier",
    "list_processes":    "processus actifs",
    "get_network_info":  "infos reseau",
    # Nouveaux outils v1.4
    "set_volume":        "reglage volume",
    "get_audio_level":   "niveau volume",
    "mute_audio":        "son muet/actif",
    "set_brightness":    "luminosite ecran",
    "get_brightness":    "lecture luminosite",
    "wifi_toggle":       "WiFi on/off",
    "analyze_screen":    "vision ecran IA",
    "open_youtube":      "ouverture YouTube",
    "search_youtube":    "recherche YouTube",
    "play_music":        "lecture musique",
    "search_flights":    "recherche vols",
    "create_plan":       "planification multi-etapes",
    "execute_plan":      "execution automatique de plan",
    # Nouveaux outils v1.5
    "delete_file":       "suppression fichier",
    "summarize":         "resume document",
    "draft_email":       "brouillon email",
    "kill_process":      "arret processus",
    "write_code":        "ecriture code",
    "run_code":          "execution code",
    "explain_code":      "explication code",
    # Jeux (v1.5)
    "open_steam":              "ouverture Steam",
    "open_epic_games":         "ouverture Epic Games",
    "list_installed_steam_games": "liste jeux Steam",
    "launch_game_steam":       "lancement jeu",
    "search_game_on_steam":    "recherche jeu Steam",
    "install_game_steam":      "installation jeu",
    # Webcam (v1.5)
    "analyze_webcam":    "analyse webcam",
    "start_auto_mute":   "activation auto-mute webcam",
    "stop_auto_mute":    "desactivation auto-mute webcam",
}


# ── Journal d'erreurs ───────────────────────────────────────────────────────
# Sans trace, une demande restée sans réponse était impossible à diagnostiquer
# (test du 18/10 : deux messages renvoyés par l'utilisateur, cause inconnue).
_ERROR_LOG = (Path(sys.executable).parent if getattr(sys, "frozen", False)
              else Path(__file__).resolve().parent) / "amah_errors.log"


def _log_error(context: str, exc: BaseException) -> None:
    """Ajoute l'erreur (avec la pile d'appels) à amah_errors.log, limité à ~500 Ko."""
    try:
        if _ERROR_LOG.exists() and _ERROR_LOG.stat().st_size > 500_000:
            _ERROR_LOG.write_text(_ERROR_LOG.read_text(encoding="utf-8", errors="replace")[-250_000:],
                                  encoding="utf-8")
        trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        with _ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] {context}\n{trace}")
    except Exception:
        pass


def _fit_window(root, width: int, height: int) -> int:
    """Taille réduite à l'écran puis fenêtre centrée ; renvoie la hauteur retenue.

    Sans position imposée, Windows place la fenêtre ~130 px sous le haut de
    l'écran : sur un portable de 720 px, le bas (bouton, barre de saisie)
    finissait sous la barre des tâches. 110 px de marge = barre de titre
    (~31) + barre des tâches (~48) + bordures.
    """
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    width, height = min(width, sw - 20), min(height, sh - 110)
    x, y = max(0, (sw - width) // 2), max(0, (sh - 80 - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    return height


class AmahGUI:
    def __init__(self, root):
        self.root       = root
        # Actions sensibles (suppression, commande, envoi...) : boite Oui/Non
        set_confirm_handler(tk_confirm_handler(self.root))
        self.root.title("The Amah — Agent Local")
        self.root.configure(bg=BG)
        _fit_window(self.root, 980, 700)
        self.root.minsize(760, 520)

        # Client Groq partage (singleton) — rotation de cles + backoff geres
        # de maniere centrale, utilises aussi par planner.py et screen_vision.py
        try:
            self.groq = GroqClient.get()
        except RuntimeError as e:
            messagebox.showerror("Cle manquante", str(e))
            sys.exit(1)

        self.session_id     = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.busy           = False
        self._last_reply    = ""
        self._tools_this_call = []   # outils utilisés dans l'appel en cours
        self._voice_mode    = False  # True = réponse vocale automatique activée

        cleanup_old_messages()                 # durée choisie (AMAH_HISTORY_DAYS, 0 = toujours)
        truncate_old_tool_results(max_chars=800)  # tronque tool_results longs en DB
        previous             = load_resume_messages()  # dernière session si < 12 h
        self.messages        = [{"role": "system", "content": SYSTEM_PROMPT}] + previous
        self._previous_count = len(previous)

        self._build_ui()
        self._bind_shortcuts()
        self._welcome()
        self._start_metrics()

        # Auto-mute webcam (v1.5) : feedback visuel quand le son est coupe/retabli
        # automatiquement (callbacks declenches depuis le thread de surveillance)
        WebcamMonitor.get().set_callbacks(
            on_pause=lambda: self.root.after(0, self._set_status, "[!] Son coupe automatiquement (plusieurs personnes detectees)", GOLD),
            on_resume=lambda: self.root.after(0, self._set_status, "[OK] Pret"),
        )

    # ── Construction de l'interface ─────────────────────────────────────────

    def _build_ui(self):
        self._build_statusbar()                           # barre du bas (pleine largeur)
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        self._build_sidebar(body)
        tk.Frame(body, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)
        self._content = tk.Frame(body, bg=BG)
        self._content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_topbar(self._content)
        tk.Frame(self._content, bg=BORDER, height=1).pack(fill=tk.X)
        self._build_chat(self._content)
        tk.Frame(self._content, bg=BORDER, height=1).pack(fill=tk.X)
        self._build_suggestions(self._content)
        tk.Frame(self._content, bg=BORDER, height=1).pack(fill=tk.X)
        self._build_input(self._content)
        self._tools_panel_visible = False
        self._build_tools_panel()

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=BG2, width=52)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack_propagate(False)

        # Logo hexagone
        tk.Button(sb, text="⬡", bg=BG2, fg=GOLD, font=("Consolas", 18),
                  relief=tk.FLAT, bd=0, padx=0, pady=6, width=3,
                  activebackground=BG4, activeforeground=GOLD2,
                  cursor="hand2").pack(fill=tk.X, pady=(10, 2), padx=2)

        tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X, padx=6, pady=6)

        def _sb(icon, label, cmd):
            return tk.Button(sb, text=f"{icon}\n{label}", bg=BG2, fg=TEXT3,
                             font=("Consolas", 7), relief=tk.FLAT, bd=0,
                             padx=0, pady=5, width=6,
                             activebackground=BG4, activeforeground=GOLD,
                             cursor="hand2", command=cmd)

        _sb("⚙", "outils",  self._toggle_tools_panel).pack(fill=tk.X, pady=1, padx=2)
        _sb("↺", "hist.",   self._nav_history).pack(fill=tk.X, pady=1, padx=2)
        _sb("◎", "mem.",    self._nav_memory).pack(fill=tk.X, pady=1, padx=2)
        _sb("⊕", "fich.",   self._nav_files).pack(fill=tk.X, pady=1, padx=2)

        tk.Frame(sb, bg=BG2).pack(fill=tk.BOTH, expand=True)   # spacer

        tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X, padx=6, pady=4)
        _sb("≡", "cfg.",    self._nav_settings).pack(fill=tk.X, pady=1, padx=2)

        # Avatar
        av = tk.Frame(sb, bg=GOLD_DIM, width=28, height=28)
        av.pack_propagate(False)
        av.pack(pady=(6, 12), padx=12)
        tk.Label(av, text="AD", bg=GOLD_DIM, fg=BG,
                 font=("Consolas", 7, "bold")).place(relx=0.5, rely=0.5, anchor="center")

    def _build_topbar(self, parent):
        tb = tk.Frame(parent, bg=BG2, height=44)
        tb.pack(fill=tk.X)
        tb.pack_propagate(False)

        # Gauche : dot de statut + texte
        left = tk.Frame(tb, bg=BG2)
        left.pack(side=tk.LEFT, padx=14, fill=tk.Y)

        self._pulse_canvas = tk.Canvas(left, width=8, height=8, bg=BG2,
                                        highlightthickness=0)
        self._pulse_canvas.pack(side=tk.LEFT, pady=(18, 0))
        self._pulse_oval = self._pulse_canvas.create_oval(1, 1, 7, 7, fill=GREEN, outline="")

        self._status_var = tk.StringVar(value="AMAH // PRET")
        self._status_lbl = tk.Label(left, textvariable=self._status_var,
                                     bg=BG2, fg=TEXT2, font=("Consolas", 9))
        self._status_lbl.pack(side=tk.LEFT, padx=(8, 0), pady=(14, 0))

        # Droite : chip modèle + boutons d'action
        right = tk.Frame(tb, bg=BG2)
        right.pack(side=tk.RIGHT, padx=10, pady=6)

        chip = tk.Frame(right, bg=BORDER, padx=6, pady=3)
        chip.pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(chip, text="Groq 70B/8B", bg=BORDER, fg=TEXT3,
                 font=("Consolas", 8)).pack()

        def _tb(text, cmd, fg=TEXT2, bg=BG2, bold=False):
            f = ("Consolas", 9, "bold") if bold else ("Consolas", 9)
            tk.Button(right, text=text, bg=bg, fg=fg, font=f,
                      relief=tk.FLAT, padx=7, pady=3,
                      activebackground=BG4, activeforeground=GOLD,
                      cursor="hand2", command=cmd).pack(side=tk.LEFT, padx=2)

        _tb("◎ mic",    self._open_voice,      fg=GOLD_DIM)
        _tb("⎘ copier", self._copy_last)
        _tb("⟳ reset",  self._reset)
        _tb("◉ AMAH", self._launch_voice_ui, fg=GOLD,  bg=GOLD_FAINT, bold=True)
        _tb("⬡ écoute", self._launch_listener, fg=CYAN,  bg="#0A1020")

    def _build_chat(self, parent):
        self._chat_wrap = tk.Frame(parent, bg=BG)
        self._chat_wrap.pack(fill=tk.BOTH, expand=True)

        self.chat = scrolledtext.ScrolledText(
            self._chat_wrap, bg=BG, fg=TEXT,
            font=("Consolas", 11), wrap=tk.WORD,
            state=tk.DISABLED, relief=tk.FLAT,
            padx=20, pady=14,
        )
        self.chat.pack(fill=tk.BOTH, expand=True)

        self.chat.tag_configure("amah_lbl",  foreground=GOLD,      font=("Consolas", 11, "bold"))
        self.chat.tag_configure("amah_txt",  foreground=TEXT,       font=("Consolas", 11))
        self.chat.tag_configure("user_lbl",  foreground=TEXT2,      font=("Consolas", 11))
        self.chat.tag_configure("user_txt",  foreground=TEXT,       font=("Consolas", 11))
        self.chat.tag_configure("dim",       foreground=GOLD_DIM,   font=("Consolas", 10))
        self.chat.tag_configure("thinking",  foreground=TEXT3,      font=("Consolas", 11, "italic"))
        self.chat.tag_configure("tool",      foreground=TEXT_TOOL,  font=("Consolas", 10, "italic"))
        self.chat.tag_configure("timestamp", foreground=TEXT3,      font=("Consolas", 9))
        self.chat.tag_configure("error",     foreground=RED,        font=("Consolas", 10))
        self.chat.tag_configure("separator", foreground=BORDER,     font=("Consolas", 8))

        self._ctx_menu = tk.Menu(self.root, tearoff=0, bg=BG2,
                                  fg=TEXT, activebackground=GOLD_DIM)
        self._ctx_menu.add_command(label="Copier la derniere reponse", command=self._copy_last)
        self._ctx_menu.add_command(label="Tout selectionner", command=self._select_all)
        self.chat.bind("<Button-3>", self._show_ctx_menu)

    def _build_suggestions(self, parent):
        bar = tk.Frame(parent, bg=BG2, pady=5)
        bar.pack(fill=tk.X)
        _CHIPS = [
            ("⊡ bureau",  "Organise mon bureau"),
            ("✉ emails",  "Lis mes 5 derniers emails"),
            ("☁ météo",   "Météo Paris aujourd'hui"),
            ("▤ Word",    "Crée un document Word"),
            ("⌕ web",     "Recherche le web"),
            ("♪ musique", "Mets de la musique"),
        ]
        for label, query in _CHIPS:
            tk.Button(bar, text=label, bg=BORDER, fg=TEXT2,
                      font=("Consolas", 8), relief=tk.FLAT, padx=8, pady=2,
                      activebackground=BORDER2, activeforeground=GOLD,
                      cursor="hand2",
                      command=lambda q=query: self._send_suggestion(q)
                      ).pack(side=tk.LEFT, padx=(8, 0), pady=3)

    def _build_input(self, parent):
        wrap = tk.Frame(parent, bg=BG, pady=10)
        wrap.pack(fill=tk.X)

        # Cadre avec bordure simulée
        outer = tk.Frame(wrap, bg=BORDER2, padx=1, pady=1)
        outer.pack(fill=tk.X, padx=16)
        box = tk.Frame(outer, bg=BG3)
        box.pack(fill=tk.X)

        self.entry = tk.Text(box, height=1, bg=BG3, fg=TEXT,
                             insertbackground=GOLD,
                             font=("Consolas", 11),
                             relief=tk.FLAT, bd=0,
                             wrap=tk.WORD)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(14, 4), pady=8)

        self._mic_btn = tk.Button(box, text="◎", bg=BG3, fg=GOLD_DIM,
                  font=("Consolas", 13), relief=tk.FLAT, padx=6, pady=3,
                  activebackground=BG4, activeforeground=GOLD,
                  cursor="hand2", command=self._open_voice)
        self._mic_btn.pack(side=tk.LEFT, padx=(0, 2))

        tk.Button(box, text="[+]", bg=BG3, fg=GOLD_DIM,
                  font=("Consolas", 10, "bold"), relief=tk.FLAT, padx=6, pady=4,
                  activebackground=BG4, activeforeground=GOLD,
                  cursor="hand2", command=self._attach_file).pack(side=tk.LEFT, padx=(0, 4))

        tk.Frame(box, bg=BORDER2, width=1).pack(side=tk.LEFT, fill=tk.Y, pady=6)

        self.btn = tk.Button(box, text="▶", bg=GOLD_DIM, fg=BG,
                             font=("Consolas", 11, "bold"), relief=tk.FLAT,
                             padx=10, pady=4, cursor="hand2",
                             activebackground=GOLD, activeforeground=BG,
                             command=self._send)
        self.btn.pack(side=tk.LEFT, padx=(4, 8))

        self.entry.bind("<Return>",     self._on_return)
        self.entry.bind("<KeyRelease>", self._resize_entry)
        self.entry.focus()

    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg=BG2, pady=3)
        sb.pack(fill=tk.X, side=tk.BOTTOM)

        self._metrics_var = tk.StringVar(value="")
        self._metrics_lbl = tk.Label(sb, textvariable=self._metrics_var,
                 bg=BG2, fg=TEXT3, font=("Consolas", 8))
        self._metrics_lbl.pack(side=tk.LEFT, padx=14)

        from groq_client import GroqClient
        _backend = GroqClient.get().backend
        _backend_color = "#00d4ff" if _backend == "LiteLLM" else TEXT3
        self._backend_lbl = tk.Label(sb, text=f"[{_backend}]",
                 bg=BG2, fg=_backend_color, font=("Consolas", 8, "bold"))
        self._backend_lbl.pack(side=tk.RIGHT, padx=(0, 6))

        tk.Label(sb, text=f"Shift+Entrée = newline  ·  Ctrl+R = reset  ·  {len(TOOL_FUNCTIONS)} outils  ·  v{CURRENT_VERSION}",
                 bg=BG2, fg=TEXT3, font=("Consolas", 8), anchor="e"
                 ).pack(side=tk.RIGHT, padx=14)

    # ── Outils panel ─────────────────────────────────────────────────────────

    def _build_tools_panel(self):
        panel = tk.Frame(self._chat_wrap, bg=BG2, relief=tk.FLAT)

        hdr = tk.Frame(panel, bg=BG2)
        hdr.pack(fill=tk.X, pady=(8, 4), padx=10)
        tk.Label(hdr, text="87 OUTILS", bg=BG2, fg=GOLD,
                 font=("Consolas", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(hdr, text="✕", bg=BG2, fg=TEXT2, font=("Consolas", 10),
                  relief=tk.FLAT, padx=4, cursor="hand2",
                  command=self._toggle_tools_panel).pack(side=tk.RIGHT)
        tk.Frame(panel, bg=BORDER, height=1).pack(fill=tk.X)

        txt = tk.Text(panel, bg=BG2, fg=TEXT2, font=("Consolas", 8),
                      wrap=tk.WORD, relief=tk.FLAT, bd=0, padx=10, pady=6)
        scrl = tk.Scrollbar(panel, command=txt.yview, bg=BG2, width=8)
        txt.config(yscrollcommand=scrl.set)
        scrl.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(fill=tk.BOTH, expand=True)

        txt.tag_configure("cat",  foreground=GOLD,  font=("Consolas", 8, "bold"))
        txt.tag_configure("tool", foreground=TEXT2,  font=("Consolas", 8))

        for cat_name, tools_list in [
            ("Fichiers",      ["list_files","organize_folder","find_files","move_file",
                               "create_folder","read_file","write_file","edit_file",
                               "edit_pdf","delete_file","get_folder_info","summarize"]),
            ("Documents",     ["create_word","create_pdf","create_txt","read_document"]),
            ("Internet",      ["web_search","read_webpage","open_browser","click_element",
                               "fill_form","get_page_text","take_screenshot",
                               "click_text","type_in_field"]),
            ("Email",         ["read_emails","send_email","search_emails","draft_email"]),
            ("Systeme",       ["get_system_info","open_file","run_command",
                               "list_processes","get_network_info","kill_process"]),
            ("Memoire",       ["save_memory","get_memories","delete_memory"]),
            ("Code",          ["write_code","run_code","explain_code"]),
            ("Hardware",      ["set_volume","get_audio_level","mute_audio",
                               "set_brightness","get_brightness","wifi_toggle"]),
            ("Vision",        ["analyze_screen","screenshot_full"]),
            ("YouTube",       ["open_youtube","search_youtube","play_music"]),
            ("Vols",          ["search_flights"]),
            ("Jeux",          ["open_steam","open_epic_games","list_installed_steam_games",
                               "launch_game_steam","search_game_on_steam","install_game_steam"]),
            ("Webcam",        ["analyze_webcam","start_auto_mute","stop_auto_mute"]),
            ("Media/Voix",    ["speak","listen","listen_continuous",
                               "send_notification","set_reminder"]),
            ("Excel",         ["read_excel","create_excel","append_to_excel"]),
            ("Utilitaires",   ["calculate","get_datetime","add_days",
                               "generate_password","convert_units"]),
            ("Archives",      ["zip_files","unzip_file","list_archive"]),
            ("Images",        ["resize_image","get_image_info","convert_image"]),
            ("Meteo",         ["get_weather","get_weather_simple"]),
            ("Traduction",    ["translate","detect_language"]),
            ("QR/Clipboard",  ["create_qrcode","read_clipboard","write_clipboard"]),
            ("Planif",        ["create_plan","execute_plan","create_daily_task","list_tasks",
                               "delete_task","run_task_now"]),
            ("Stats/MAJ",     ["get_stats","reset_stats","check_update",
                               "get_current_version","get_license_info"]),
        ]:
            txt.insert(tk.END, f"\n{cat_name}\n", "cat")
            for t in tools_list:
                txt.insert(tk.END, f"  {t}\n", "tool")
        txt.config(state=tk.DISABLED)
        self._tools_panel = panel

    def _toggle_tools_panel(self):
        if self._tools_panel_visible:
            self._tools_panel.place_forget()
            self._tools_panel_visible = False
        else:
            self._tools_panel.place(x=0, y=0, relheight=1, width=280)
            self._tools_panel_visible = True

    # ── Sidebar actions ───────────────────────────────────────────────────────

    def _send_suggestion(self, text: str):
        if self.busy:
            return
        self.entry.delete("1.0", tk.END)
        self.entry.insert("1.0", text)
        self._send()

    def _nav_history(self):
        self._write(("\n  — Historique récent —\n", "dim"))
        count = 0
        for m in self.messages[1:]:
            if m["role"] in ("user", "assistant") and count < 8:
                who = "Toi" if m["role"] == "user" else "Amah"
                content = str(m.get("content") or "")[:70].replace("\n", " ")
                self._write((f"  {who}: {content}\n", "tool"))
                count += 1
        self._write(("\n", "dim"))

    def _nav_memory(self):
        if not self.busy:
            self.entry.delete("1.0", tk.END)
            self.entry.insert("1.0", "Montre-moi tout ce que tu as mémorisé")
            self._send()

    def _nav_files(self):
        if not self.busy:
            self.entry.delete("1.0", tk.END)
            self.entry.insert("1.0", "Liste les fichiers de mon bureau")
            self._send()

    def _nav_settings(self):
        self._write(("\n  Paramètres : édite le fichier .env pour changer les clés API.\n\n", "dim"))

    def _refresh_backend_lbl(self):
        """Met a jour le badge [Groq] / [LiteLLM] si un fallback s'est produit."""
        if not hasattr(self, '_backend_lbl'):
            return
        from groq_client import GroqClient
        _backend = GroqClient.get().backend
        _color   = "#00d4ff" if _backend == "LiteLLM" else TEXT3
        self._backend_lbl.config(text=f"[{_backend}]", fg=_color)

    def _pulse_dot(self):
        """Anime le point de statut dans la topbar (pulse lent)."""
        if not hasattr(self, '_pulse_canvas'):
            return
        try:
            cur = self._pulse_canvas.itemcget(self._pulse_oval, "fill")
            nxt = GREEN if cur != GREEN else "#1A4A2A"
            self._pulse_canvas.itemconfig(self._pulse_oval, fill=nxt)
        except Exception:
            pass
        self.root.after(900, self._pulse_dot)

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
            self._write((f"  {self._previous_count} messages précédents chargés.\n\n", "dim"))
        self._write_msg("Amah >", "Tu m'as trouvée. Qu'est-ce que tu veux faire ?", "amah_lbl", "amah_txt")
        self._write(("  Shift+Entrée = retour ligne  ·  ⚙ = liste outils  ·  [+] = fichier\n\n", "dim"))
        self._set_status("[OK] Pret")
        self._pulse_dot()

    def _set_status(self, text: str, color: str = None):
        clean   = text.replace("[OK] ", "").replace("[!] ", "⚠ ")
        display = f"AMAH // {clean.upper()}"
        self._status_var.set(display)
        if not hasattr(self, '_status_lbl'):
            return
        if color:
            self._status_lbl.config(fg=color)
        elif "PRET" in display or "COPIE" in display:
            self._status_lbl.config(fg=GREEN)
        elif "⚠" in display or "ERREUR" in display:
            self._status_lbl.config(fg=RED)
        else:
            self._status_lbl.config(fg=GOLD)
        try:
            dot = RED if ("⚠" in display or "ERREUR" in display) else GREEN
            self._pulse_canvas.itemconfig(self._pulse_oval, fill=dot)
        except Exception:
            pass

    def _start_metrics(self):
        """Lance le monitoring CPU/RAM en arrière-plan (mise à jour toutes les 2s)."""
        import time

        def _loop():
            while True:
                try:
                    import psutil
                    cpu = psutil.cpu_percent(interval=1)
                    ram = psutil.virtual_memory().percent
                    text  = f"CPU {cpu:.0f}%  RAM {ram:.0f}%"
                    color = RED if (cpu >= 85 or ram >= 85) else (GOLD if (cpu >= 65 or ram >= 65) else GREEN)
                    self.root.after(0, self._metrics_var.set, text)
                    self.root.after(0, self._metrics_lbl.config, {"fg": color})
                except Exception:
                    pass
                time.sleep(2)

        threading.Thread(target=_loop, daemon=True).start()

    def _open_voice(self):
        """Ouvre l'interface vocale HUD animée. Active le mode voix (réponse orale auto)."""
        if self.busy:
            return
        try:
            from voice_ui import VoiceWindow
        except ImportError as e:
            self._write((f"  Erreur import voice_ui : {e}\n\n", "error"))
            return

        self._voice_mode = True  # active la réponse vocale pour ce cycle

        def on_result(text: str):
            self.entry.delete("1.0", tk.END)
            self.entry.insert("1.0", text)
            self._send()

        VoiceWindow(self.root, on_result)

    def _attach_file(self):
        """Ouvre un sélecteur de fichier et insère le chemin dans le champ de saisie."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Joindre un fichier",
            filetypes=[
                ("Tous les fichiers", "*.*"),
                ("Documents", "*.pdf *.docx *.txt *.doc"),
                ("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("Code", "*.py *.js *.html *.css *.json *.xml *.csv"),
                ("Excel", "*.xlsx *.xls"),
            ]
        )
        if path:
            current = self.entry.get("1.0", tk.END).strip()
            self.entry.delete("1.0", tk.END)
            prefix = current + "\n" if current else ""
            self.entry.insert("1.0", f'{prefix}"{path}"')
            self.entry.focus()
            self._resize_entry()

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
        # "end-1c" (juste avant le retour à la ligne final implicite du widget,
        # là où insert(END, ...) écrit réellement) et non tk.END : sinon la
        # marque finit après le texte inséré et delete(mark, END) ne supprime
        # jamais le placeholder "réfléchit..." (il restait affiché à chaque tour).
        self.chat.mark_set("thinking_start", "end-1c")
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
        last_user = next(
            (m["content"] for m in reversed(self.messages) if m["role"] == "user"), ""
        )

        # Heure, date, calcul simple : réponse locale immédiate, sans appel IA
        instant = instant_reply(last_user)
        if instant:
            self._finish_local_reply(instant)
            return

        # "Tu te souviens de ce qu'on avait dit sur…" : rappel de l'historique
        try:
            memory, direct = memory_context(last_user, summarize_fn=self._summarize_memory)
        except Exception as e:
            _log_error(f"memoire | {last_user[:120]!r}", e)
            memory, direct = None, False
        if memory and direct:
            recalled = format_recall(memory)
            if recalled:
                self._finish_local_reply(recalled)
                return
        system_original = None
        instruction = memory_instruction(memory) if memory else ""
        if instruction:
            system_original = self.messages[0]["content"]
            self.messages[0]["content"] = system_original + instruction

        tools  = self._select_tools(last_user)
        stream = self._is_simple_query(last_user, tools)
        try:
            if stream:
                reply, started = self._chat_stream()
                finish = self._finish_streamed_reply if started else self._show_reply
            else:
                reply  = self._chat(last_user, tools)
                finish = self._show_reply
            self.messages.append({"role": "assistant", "content": reply})
            save_message(self.session_id, "assistant", reply)
            self.root.after(0, finish, reply)
        except Exception as e:
            _log_error(f"chat | {last_user[:120]!r}", e)
            self.root.after(0, self._show_error, self._format_error(str(e)))
        finally:
            # La mémoire ne sert qu'à ce tour : ne pas l'accumuler dans le prompt
            if system_original is not None:
                self.messages[0]["content"] = system_original

    def _finish_local_reply(self, reply: str):
        """Réponse produite sans appel IA (instantanée ou mémoire)."""
        self.messages.append({"role": "assistant", "content": reply})
        save_message(self.session_id, "assistant", reply)
        self.root.after(0, self._show_reply, reply)

    def _summarize_memory(self, prompt: str) -> str:
        """Synthèse JSON demandée par le rappel de mémoire (sans outils)."""
        response = self.groq.chat(
            [{"role": "system", "content": MEMORY_SUMMARY_SYSTEM},
             {"role": "user", "content": prompt}],
            model=MODEL, max_tokens=900, temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def _is_simple_query(self, text: str, tools) -> bool:
        """Conversation pure (le routeur n'a proposé aucun outil) -> réponse
        rapide en streaming par le 20b. Une vraie question factuelle reçoit au
        moins le lot d'outils par défaut (dont web_search) et passe par _chat."""
        return tools is None

    def _chat_stream(self):
        """Reponse en streaming pour les questions simples/conversationnelles
        (8B, sans outils) : le texte apparait au fur et a mesure plutot que
        d'attendre la reponse complete avant l'effet machine a ecrire — la
        latence percue est nettement reduite. Retourne (texte, a_diffuse)."""
        self._trim_messages()
        self.root.after(0, self._set_status, "Amah reflechit...")

        full    = []
        started = [False]
        try:
            # Prompt court (~200 tokens) : la conversation pure n'a pas besoin
            # des règles d'outils de SYSTEM_PROMPT (~3 700 tokens par message).
            stream = self.groq.chat(
                chat_messages(self.messages), model="openai/gpt-oss-20b",
                max_tokens=1024, temperature=0.4, stream=True,
                on_status=lambda txt: self.root.after(0, self._set_status, txt),
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    if not started[0]:
                        started[0] = True
                        self.root.after(0, self._start_stream_ui)
                    full.append(delta)
                    self.root.after(0, self._append_stream_chunk, delta)
        except Exception:
            if not full:
                raise
        return "".join(full) or "...", started[0]

    def _start_stream_ui(self):
        self.chat.config(state=tk.NORMAL)
        self.chat.delete("thinking_start", tk.END)
        self.chat.config(state=tk.DISABLED)
        self._write((f"[{self._ts()}] ", "timestamp"), ("Amah > ", "amah_lbl"))

    def _append_stream_chunk(self, text: str):
        self.chat.config(state=tk.NORMAL)
        self.chat.insert(tk.END, text, "amah_txt")
        self.chat.see(tk.END)
        self.chat.config(state=tk.DISABLED)

    def _finish_streamed_reply(self, reply):
        self._last_reply = reply
        self._write(("\n\n", "amah_txt"))
        self._after_reply()

    def _format_error(self, error: str) -> str:
        if "rate_limit_exceeded" in error or "Rate limit" in error:
            import re
            # ".+?\." s'arretait au premier point rencontre -- "7.66s." donnait
            # "7" au lieu de "7.66s". On exige un point SUIVI d'un espace pour
            # cibler la fin de la duree (".66s. Visite..." -> "7.66s").
            wait = re.search(r"try again in (.+?)\.\s", error)
            temps = wait.group(1) if wait else "quelques instants"
            # Groq distingue les limites "par minute" (TPM/RPM -- throttling
            # court qui se debloque tout seul en quelques secondes) des limites
            # "par jour" (TPD/RPD -- vraie penurie de quota). Annoncer "limite
            # quotidienne... attends 7 secondes" est contradictoire et alarme
            # inutilement l'utilisateur pour un simple ralentissement passager.
            if re.search(r"per day|tokens per day|requests per day|TPD|RPD",
                         error, re.IGNORECASE):
                return (
                    f"Limite quotidienne Groq atteinte.\n"
                    f"Attends {temps} avant de continuer.\n"
                    f"Ou cree un 2eme compte gratuit sur console.groq.com"
                )
            return (
                f"Limite Groq temporaire (quelques requetes par minute).\n"
                f"Patiente {temps}, ca se debloque tout seul -- "
                f"pas besoin d'attendre jusqu'a demain."
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
        self.chat.config(state=tk.NORMAL)
        self.chat.delete("thinking_start", tk.END)
        self.chat.config(state=tk.DISABLED)
        if self._tools_this_call:
            outils = " → ".join(self._tools_this_call)
            self._write((f"  [ {outils} ]\n", "tool"))
        self._tools_this_call = []
        self._write((f"[{self._ts()}] ", "timestamp"), ("Amah > ", "amah_lbl"))
        self._typewrite(reply + "\n\n", "amah_txt", callback=self._after_reply)

    def _typewrite(self, text: str, tag: str, callback=None):
        """Affiche le texte progressivement (effet machine a ecrire, ~0.1 sec total).
        Reduit de ~1.2s a ~0.1s : ce delai etait purement cosmetique et s'ajoutait
        a chaque reponse 70B, au-dessus de la latence reelle de l'API -- une
        bonne partie de la "lenteur" ressentie n'etait pas du tout liee a Groq."""
        tick_ms = 5
        n_ticks = 20
        chunk   = max(1, len(text) // n_ticks)
        idx     = [0]

        def _tick():
            if idx[0] < len(text):
                end = min(idx[0] + chunk, len(text))
                self.chat.config(state=tk.NORMAL)
                self.chat.insert(tk.END, text[idx[0]:end], tag)
                self.chat.see(tk.END)
                self.chat.config(state=tk.DISABLED)
                idx[0] = end
                self.root.after(tick_ms, _tick)
            elif callback:
                callback()

        _tick()

    def _after_reply(self):
        self._write_separator()
        self._unlock()
        self._set_status("[OK] Pret")
        self._refresh_backend_lbl()
        # Si la question venait du micro, Amah répond aussi à voix haute
        if self._voice_mode and self._last_reply:
            self._voice_mode = False
            threading.Thread(
                target=self._speak_reply,
                args=(self._last_reply,),
                daemon=True
            ).start()

    def _speak_reply(self, text: str):
        """Fait parler Amah après une interaction vocale (200 premiers chars)."""
        try:
            from tools.voice import speak
            short = text[:220].replace("\n", " ")
            res = speak(short, speed=1)
            if "error" in res:
                self.root.after(0, self._set_status, "[!] Voix indisponible", "#cc4444")
        except Exception as e:
            self.root.after(0, self._set_status, f"[!] Voix indisponible : {e}"[:60], "#cc4444")

    def _show_error(self, error):
        self.chat.config(state=tk.NORMAL)
        self.chat.delete("thinking_start", tk.END)
        self.chat.config(state=tk.DISABLED)
        self._write((f"  Erreur : {error}\n\n", "error"))
        self._unlock()
        self._set_status("[!] Erreur")

    def _unlock(self):
        self.busy = False
        self.entry.config(state=tk.NORMAL)
        self.btn.config(state=tk.NORMAL)
        self.entry.focus()

    # ── Actions ──────────────────────────────────────────────────────────────

    def _launch_voice_ui(self):
        """Lance l'interface vocale plein écran dans un processus séparé."""
        import subprocess as _sp
        voice_script = str(Path(__file__).parent / "voice_fullscreen.py")
        _sp.Popen([sys.executable, voice_script],
                  creationflags=_sp.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        self._set_status("Interface vocale lancee — dis 'ferme' pour quitter")

    def _launch_listener(self):
        """Lance le listener de mot de réveil (widget coin bas-droit)."""
        import subprocess as _sp
        listener_script = str(Path(__file__).parent / "amah_listener.py")
        if not Path(listener_script).exists():
            messagebox.showerror("Erreur", "amah_listener.py introuvable")
            return
        _sp.Popen([sys.executable, listener_script],
                  creationflags=_sp.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        self._set_status("Amah ecoute en arriere-plan — dis 'Amah' pour l'appeler")

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
            "Fichiers":    ["list_files","organize_folder","find_files","move_file",
                            "create_folder","read_file","write_file","edit_file",
                            "edit_pdf","delete_file","get_folder_info","summarize"],
            "Documents":   ["create_word","create_txt","create_pdf","read_document"],
            "Internet":    ["web_search","read_webpage","open_browser","click_element",
                            "fill_form","take_screenshot","get_page_text",
                            "click_text","type_in_field"],
            "Email":       ["read_emails","send_email","search_emails","draft_email"],
            "Systeme":     ["get_system_info","open_file","run_command",
                            "list_processes","get_network_info","kill_process"],
            "Memoire":     ["save_memory","get_memories","delete_memory"],
            "Code":        ["write_code","run_code","explain_code"],
            "Hardware":    ["set_volume","get_audio_level","mute_audio",
                            "set_brightness","get_brightness","wifi_toggle"],
            "Vision":      ["analyze_screen","screenshot_full"],
            "YouTube":     ["open_youtube","search_youtube","play_music"],
            "Vols":        ["search_flights"],
            "Jeux":        ["open_steam","open_epic_games","list_installed_steam_games",
                            "launch_game_steam","search_game_on_steam","install_game_steam"],
            "Webcam":      ["analyze_webcam","start_auto_mute","stop_auto_mute"],
            "Planif":      ["create_plan","execute_plan","create_daily_task","list_tasks","delete_task","run_task_now"],
        }
        self._write((f"\n  — {len(TOOL_FUNCTIONS)} outils disponibles —\n\n", "dim"))
        for cat, tools in cats.items():
            self._write((f"  {cat}: ", "amah_lbl"),
                        (" · ".join(tools) + "\n", "dim"))
        self._write(("\n", "dim"))

    # ── Moteur de chat ────────────────────────────────────────────────────────

    def _retry_with_repaired_tool_call(self, repaired):
        """Execute l'appel d'outil recupere par repair_tool_use_failed(), ajoute
        son resultat a la conversation, et relance Groq pour obtenir une vraie
        reponse au lieu de l'erreur 400 brute."""
        name, args = repaired
        tc = SimpleNamespace(id="call_fixed",
                              function=SimpleNamespace(name=name, arguments=json.dumps(args, ensure_ascii=False)))
        self.messages.append({
            "role":    "assistant",
            "content": "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": name, "arguments": tc.function.arguments}}],
        })
        result = self._execute_tool(tc)
        if len(result) > 2000:
            result = result[:2000] + "\n...[tronqué pour économiser les tokens]"
        self.messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        self._trim_messages()
        return self._groq_call(self.messages, tools=TOOLS_DEFINITIONS, model_override=MODEL)

    def _execute_tool(self, tool_call) -> str:
        name = resolve_tool_name(tool_call.function.name)
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
            if name == "execute_plan":
                args["on_status"] = lambda txt: self.root.after(0, self._set_status, txt)
            result = func(**args)
            if name == "analyze_webcam" and isinstance(result, dict) and result.get("image_path"):
                self.root.after(0, self._show_webcam_popup, result["image_path"])
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _show_webcam_popup(self, image_path: str):
        """Ouvre un apercu webcam en direct (avec indicateur EN DIRECT)."""
        from tools.webcam import acquire, release, read_locked

        try:
            from PIL import Image, ImageTk
            import cv2
        except Exception:
            return

        cap = acquire()

        win = tk.Toplevel(self.root)
        win.title("Amah voit en direct..." if cap else "Amah voit...")
        win.configure(bg=BG)
        win.resizable(False, False)

        if cap:
            header = tk.Frame(win, bg=BG)
            header.pack(fill=tk.X, padx=8, pady=(8, 0))
            dot = tk.Canvas(header, width=10, height=10, bg=BG, highlightthickness=0, bd=0)
            dot.create_oval(1, 1, 9, 9, fill="#E03030", outline="")
            dot.pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(header, text="EN DIRECT", bg=BG, fg="#E03030",
                     font=("Consolas", 9, "bold")).pack(side=tk.LEFT)

        img_lbl = tk.Label(win, bg=BG)
        try:
            init_img = Image.open(image_path)
            init_img.thumbnail((480, 360))
            init_photo = ImageTk.PhotoImage(init_img)
            img_lbl.configure(image=init_photo)
            img_lbl.image = init_photo
        except Exception:
            pass
        img_lbl.pack(padx=8, pady=8)

        def _on_close():
            if cap:
                release()
            win.destroy()

        tk.Button(win, text="Fermer", command=_on_close, bg=BG3, fg=GOLD,
                  font=("Consolas", 9), relief=tk.FLAT, padx=10, pady=3,
                  activebackground=BG4).pack(pady=(0, 8))
        win.protocol("WM_DELETE_WINDOW", _on_close)

        if not cap:
            win.after(15000, win.destroy)
            return

        def _update_frame():
            if not win.winfo_exists():
                return
            try:
                frame = read_locked()
                if frame is not None:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(rgb)
                    img.thumbnail((480, 360))
                    photo = ImageTk.PhotoImage(img)
                    img_lbl.configure(image=photo)
                    img_lbl.image = photo
            except Exception:
                pass
            win.after(100, _update_frame)

        win.after(60000, _on_close)  # coupure auto apres 60s (vie privee)
        win.after(100, _update_frame)

    def _select_tools(self, message: str):
        """Outils à proposer (routeur partagé tools/tool_router.py), ou None pour
        une conversation pure (salutation, remerciement)."""
        tools, self._router_info = select_tools(message, TOOLS_DEFINITIONS)
        return tools or None

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

    def _groq_call(self, messages, tools=None, model_override=None, tool_choice=None):
        """Appel Groq via le client partage (rotation de cles + retry backoff geres
        de maniere centrale dans GroqClient — voir groq_client.py).
        model_override : force un modèle spécifique (ex: 8B pour questions simples)
        tool_choice : outil imposé (ex. web_search pour une question d'actualité)
        """
        return self.groq.chat(
            messages, model=model_override or MODEL, tools=tools, tool_choice=tool_choice,
            max_tokens=4096, temperature=0.4,
            on_status=lambda txt: self.root.after(0, self._set_status, txt),
        )

    def _chat(self, last_user: str, tools) -> str:
        self._trim_messages()

        # ── Sélection du modèle selon la complexité ───────────────────────────
        # Les questions simples/conversationnelles (8B, sans outils) sont
        # interceptées en amont par _run_chat et passent par _chat_stream ;
        # ici il ne reste que les tâches qui nécessitent le 70B (avec ou
        # sans outils ciblés).
        if not tools:
            active_model = MODEL
            # Filet par défaut quand aucune catégorie de mots-clés n'a matché :
            # uniquement des outils de LECTURE / information, sans effet de bord.
            # Les outils a action ou sensibles (send_email, run_command, speak,
            # open_file, save_memory, open_youtube...) sont VOLONTAIREMENT exclus
            # d'ici : ils ont deja leur propre categorie (email/systeme/media...)
            # qui se charge quand des mots-cles pertinents apparaissent. Les
            # laisser dans ce filet generique a deja cause un envoi d'email et
            # une synthese vocale non sollicites pendant une simple conversation
            # ("parle-moi de toi" -> le modele a hallucine des appels d'outils
            # juste parce qu'ils etaient disponibles).
            DEFAULT_TOOLS = {
                "web_search","read_webpage","list_files","read_file",
                "get_datetime","calculate","get_memories",
                "get_system_info",
                "get_weather","get_weather_simple",   # météo souvent demandée
                "translate",
            }
            tools = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] in DEFAULT_TOOLS]
            self.root.after(0, self._set_status, "Amah reflechit...")
        else:
            active_model = MODEL
            self.root.after(0, self._set_status, "Amah reflechit (outils cibles)...")

        try:
            # Question d'actualité sans outil précis : recherche web imposée, sinon
            # gpt-oss répond de mémoire avec des faits périmés (test du 18/10).
            forced = forced_tool(last_user, tools or [], getattr(self, "_router_info", None))
            choice = {"type": "function", "function": {"name": forced}} if forced else None
            response = self._groq_call(self.messages, tools=tools, model_override=active_model,
                                       tool_choice=choice)
        except Exception as e:
            # Quand le modele tente d'appeler un outil hors de la sous-liste
            # ciblee, Groq rejette l'appel avec une erreur 400 AVANT meme de
            # renvoyer finish_reason="tool_calls" -- le filet ci-dessous ne
            # peut donc jamais s'en charger. On relance avec tous les outils
            # plutot que de remonter cette erreur a l'utilisateur.
            if "not in request.tools" in str(e):
                _rep = repair_tool_use_failed(e)
                if _rep:
                    _extra = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] == resolve_tool_name(_rep[0])]
                    tools = list(tools or []) + _extra
                else:
                    tools = TOOLS_DEFINITIONS
                response = self._groq_call(self.messages, tools=tools, model_override=MODEL)
            else:
                # Autre cas de 400 AVANT reponse : le modele a emis un appel
                # d'outil malforme en texte brut (tool_use_failed). On tente
                # de le reparer plutot que de remonter l'erreur brute.
                repaired = repair_tool_use_failed(e)
                if repaired is None:
                    raise
                response = self._retry_with_repaired_tool_call(repaired)

        # Si le modèle réclame un outil hors de la sous-liste → relancer avec tous (70B)
        if response.choices[0].finish_reason == "tool_calls":
            tool_names = {resolve_tool_name(tc.function.name) for tc in (response.choices[0].message.tool_calls or [])}
            available  = {t["function"]["name"] for t in (tools or [])}
            if not tool_names.issubset(available):
                _missing = tool_names - available
                _extra   = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] in _missing]
                tools    = list(tools or []) + _extra
                response = self._groq_call(self.messages, tools=tools, model_override=MODEL)

        while response.choices[0].finish_reason == "tool_calls":
            msg = response.choices[0].message
            if not msg.tool_calls:
                break

            msg_dict = {
                "role":    "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": resolve_tool_name(tc.function.name), "arguments": tc.function.arguments}}
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
            # Reutilise la sous-liste d'outils ciblee (et non TOOLS_DEFINITIONS,
            # ~4200 tokens pour les 99 outils) pour eviter de depasser le TPM
            # Groq (12000) sur les enchainements multi-outils -- avec repli sur
            # la liste complete si le modele reclame un outil hors de cette sous-liste.
            try:
                response = self._groq_call(self.messages, tools=tools,
                                           model_override=MODEL)  # toujours 70B pour tool use
            except Exception as e:
                if "not in request.tools" in str(e):
                    # Ajoute uniquement l'outil manquant au lieu d'envoyer les 99.
                    # (Pas d'import local ici : il rendait repair_tool_use_failed
                    # "variable locale" dans tout _chat, et la réparation du
                    # premier appel plantait en UnboundLocalError.)
                    repaired = repair_tool_use_failed(e)
                    if repaired:
                        missing_name = resolve_tool_name(repaired[0])
                        extra = [t for t in TOOLS_DEFINITIONS
                                 if t["function"]["name"] == missing_name]
                        tools = list(tools or []) + extra
                    else:
                        tools = TOOLS_DEFINITIONS
                    response = self._groq_call(self.messages, tools=tools,
                                               model_override=MODEL)
                else:
                    raise
            if response.choices[0].finish_reason == "tool_calls":
                tool_names = {resolve_tool_name(tc.function.name) for tc in (response.choices[0].message.tool_calls or [])}
                available  = {t["function"]["name"] for t in (tools or [])}
                if not tool_names.issubset(available):
                    # Ajoute uniquement les outils manquants au lieu des 99
                    missing = tool_names - available
                    extra   = [t for t in TOOLS_DEFINITIONS
                               if t["function"]["name"] in missing]
                    tools   = list(tools or []) + extra
                    response = self._groq_call(self.messages, tools=tools,
                                               model_override=MODEL)

        # Cas particulier : modèle a émis l'appel d'outil en texte brut
        # format <function>nom</function>{"arg":...} au lieu de finish_reason="tool_calls"
        import re as _re
        _content = response.choices[0].message.content or ""
        _m = _re.match(
            r'^<function>([\w]+)</function>\s*(\{.*\})\s*$',
            _content.strip(), _re.DOTALL
        )
        if _m:
            _tname, _targs = _m.group(1), _m.group(2)
            try:
                _fake = SimpleNamespace(
                    id="txt-repair-0",
                    function=SimpleNamespace(name=_tname, arguments=_targs),
                )
                _res = self._execute_tool(_fake)
                if len(_res) > 2000:
                    _res = _res[:2000] + "\n...[tronqué]"
                self.messages.append({
                    "role": "assistant", "content": "",
                    "tool_calls": [{"id": "txt-repair-0", "type": "function",
                                    "function": {"name": _tname, "arguments": _targs}}],
                })
                self.messages.append({
                    "role": "tool", "tool_call_id": "txt-repair-0",
                    "content": _res,
                })
                self._trim_messages()
                _ext = list(tools or [])
                _have = {t["function"]["name"] for t in _ext}
                if _tname not in _have:
                    _ext += [t for t in TOOLS_DEFINITIONS if t["function"]["name"] == _tname]
                response = self._groq_call(self.messages, tools=_ext, model_override=MODEL)
            except Exception:
                pass

        return response.choices[0].message.content or ""


# ── Écran de configuration (premier lancement) ──────────────────────────────

# Durées proposées dans l'écran de configuration -> AMAH_HISTORY_DAYS (0 = toujours)
HISTORY_CHOICES = {"30 jours": 30, "90 jours": 90, "1 an": 365, "Toujours": 0}


class SetupWindow:
    def __init__(self, root, on_complete, env_path):
        self.root        = root
        self.on_complete = on_complete
        self.env_path    = env_path

        self.root.title("Amah Agent — Configuration")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(False, True)
        self._build()
        # Hauteur selon le contenu, sans dépasser l'écran (le formulaire défile)
        self.root.update_idletasks()
        need = sum(c.winfo_reqheight() for c in self.root.winfo_children()
                   if c is not self._form_holder) + self._form.winfo_reqheight() + 4
        _fit_window(self.root, 660, need)
        self.root.bind("<Return>", lambda e: self._save())

    def _build(self):
        hdr = tk.Frame(self.root, bg=BG_PANEL, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="THE AMAH — PREMIER LANCEMENT",
                 bg=BG_PANEL, fg=GOLD, font=("Consolas", 13, "bold")).pack()
        tk.Label(hdr, text="Configure tes acces pour demarrer",
                 bg=BG_PANEL, fg=TEXT_DIM, font=("Consolas", 9)).pack()
        tk.Label(hdr, text=f"v{CURRENT_VERSION}  ·  {len(TOOL_FUNCTIONS)} outils  ·  Windows 11",
                 bg=BG_PANEL, fg=GOLD_DIM, font=("Consolas", 8)).pack()
        tk.Frame(self.root, bg=GOLD_DIM, height=1).pack(fill=tk.X)

        # Bas de fenêtre fixe : message d'erreur et bouton toujours visibles.
        # Sur un écran de 720 px de haut, le formulaire demande ~920 px
        # et le bouton "Demarrer Amah" sortait de la fenêtre (impossible de
        # terminer la configuration).
        footer = tk.Frame(self.root, bg=BG_DARK, pady=8)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Frame(self.root, bg=GOLD_DIM, height=1).pack(side=tk.BOTTOM, fill=tk.X)

        # Formulaire défilant (barre + molette) si l'écran est trop petit
        holder = tk.Frame(self.root, bg=BG_DARK)
        holder.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(holder, bg=BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(holder, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        body = tk.Frame(canvas, bg=BG_DARK, padx=28, pady=14)
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")
        self._form_holder, self._form = holder, body
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(body_id, width=e.width))
        self.root.bind_all("<MouseWheel>",
                           lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

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

        self._lbl(body, "Cle Groq n2", "optionnel · 2e compte Groq = quota doublé")
        self.v_groq2 = tk.StringVar()
        tk.Entry(body, textvariable=self.v_groq2, show="*", **self._es()).pack(fill=tk.X, pady=(0, 10))

        self._lbl(body, "Cle Groq n3", "optionnel · 3e compte Groq = quota triplé")
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
        self.v_gmail = tk.StringVar(value="")
        tk.Entry(body, textvariable=self.v_gmail, **self._es()).pack(fill=tk.X, pady=(0, 10))

        self._lbl(body, "Mot de passe application Gmail",
                  "optionnel · Compte Google > Securite > Mots de passe des applications")
        self.v_pwd = tk.StringVar()
        tk.Entry(body, textvariable=self.v_pwd, show="*", **self._es()).pack(fill=tk.X, pady=(0, 10))

        # Durée de conservation des conversations, choisie par chaque client
        self._lbl(body, "Conserver les conversations",
                  "Amah s'en sert pour se souvenir de vos échanges · modifiable ensuite dans .env")
        self.v_history = tk.StringVar(value="1 an")
        history_menu = tk.OptionMenu(body, self.v_history, *HISTORY_CHOICES)
        history_menu.config(bg="#2a2a27", fg=GOLD, activebackground="#3a3a35", activeforeground=GOLD,
                            relief=tk.FLAT, highlightthickness=0, font=("Consolas", 10), cursor="hand2")
        history_menu.pack(anchor="w", pady=(0, 14))

        # ── Erreur + bouton ───────────────────────────────────────────────────
        self.v_err = tk.StringVar()
        tk.Label(footer, textvariable=self.v_err, bg=BG_DARK,
                 fg=RED, font=("Consolas", 10)).pack(pady=(0, 6))

        tk.Button(footer, text="Demarrer Amah", bg=GOLD_DIM, fg=BG_DARK,
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
        lines.append(f"AMAH_HISTORY_DAYS={HISTORY_CHOICES[self.v_history.get()]}\n")

        self.env_path.write_text(''.join(lines), encoding='utf-8')
        load_dotenv(self.env_path, override=True)
        self.root.unbind_all("<MouseWheel>")
        self.root.unbind("<Return>")
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
        _fit_window(self.root, 640, 440)
        self.root.resizable(False, False)
        self._build()

    def _build(self):
        # En-tête
        hdr = tk.Frame(self.root, bg=BG_PANEL, pady=14)
        hdr.pack(fill=tk.X)


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
            body = f"CRASH AMAH AGENT\n\n{tb}\n\nVersion: {CURRENT_VERSION}\nDate: {datetime.now()}"
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
        root.resizable(True, True)
        AmahGUI(root)      # taille et position : _fit_window dans AmahGUI

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
