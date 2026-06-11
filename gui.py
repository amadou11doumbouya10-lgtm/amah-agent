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
from groq_client import GroqClient
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS
from tools import TOOL_FUNCTIONS
from tools.memory import save_message, load_recent_messages, cleanup_old_messages, truncate_old_tool_results
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


class AmahGUI:
    def __init__(self, root):
        self.root       = root
        self.root.title("The Amah — Agent Local")
        self.root.configure(bg=BG)
        self.root.geometry("980x700")
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

        cleanup_old_messages(days=90)          # purge messages > 90 jours
        truncate_old_tool_results(max_chars=800)  # tronque tool_results longs en DB
        previous             = load_recent_messages(limit=10)  # 10 suffisent
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

        tk.Label(sb, text="Shift+Entrée = newline  ·  Ctrl+R = reset  ·  87 outils  ·  v1.5",
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
            self.root.after(0, self._show_error, self._format_error(str(e)))

    def _is_simple_query(self, text: str, tools) -> bool:
        """Question courte et purement conversationnelle (salutation, accuse de
        reception...) -> reponse rapide par le 8B sans outils, eligible au
        streaming. On retire volontairement qui/quand/combien/pourquoi/comment/
        c'est quoi : ces mots servent autant a des phrases sociales qu'a de
        vraies questions factuelles, qui doivent passer par le 70B + web_search
        (REGLE FACTUELLE du system prompt) pour eviter les reponses inventees."""
        SIMPLE_PATTERNS = {
            "bonjour","bonsoir","salut","hello","hi","merci","ok","oui","non",
            "dis","repete","aide","help","test","essai",
        }
        words_lower = set(text.lower().replace("'", " ").split())
        return (len(text.split()) <= 6 and
                bool(words_lower & SIMPLE_PATTERNS) and
                not tools)

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
            stream = self.groq.chat(
                self.messages, model="llama-3.1-8b-instant",
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
        """Affiche le texte progressivement (effet machine a ecrire, ~1.2 sec total)."""
        tick_ms = 20
        n_ticks = 60
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
        self._write(("\n  — 99 outils disponibles —\n\n", "dim"))
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
        # écriture / modification de fichiers → systeme ou fichiers
        "modifie":"fichiers","modifier":"fichiers","change":"fichiers","changer":"fichiers",
        "ecris":"fichiers","ecrire":"fichiers","remplace":"fichiers","remplacer":"fichiers",
        "corrige":"fichiers","corriger":"fichiers","mets":"fichiers","mettre":"fichiers",
        "insere":"fichiers","inserer":"fichiers","ajoute":"fichiers","ajouter":"fichiers",
        "supprime-ligne":"fichiers","edite":"fichiers","editer":"fichiers",
        # extensions de fichiers → toujours catégorie fichiers
        "html":"fichiers","htm":"fichiers","index":"fichiers","css":"fichiers",
        "js":"fichiers","py":"fichiers","json":"fichiers","xml":"fichiers",
        "csv":"fichiers","log":"fichiers","ini":"fichiers","cfg":"fichiers",
        "exe":"fichiers","bat":"fichiers","sh":"fichiers","md":"fichiers",
        # documents
        "word":"documents","pdf":"documents","txt":"documents","document":"documents",
        "rapport":"documents","cree":"documents","creer":"documents","genere":"documents",
        "generer":"documents","redige":"documents","rediger":"documents","ecrit":"documents",
        "ecrire":"documents","prepare":"documents",
        "write":"documents","create":"documents","make":"documents","resume":"documents",
        "synthese":"documents","lettre":"documents","contrat":"documents","facture":"documents",
        # internet / navigateur
        "web":"internet","recherche":"internet","rechercher":"internet","site":"internet",
        "navigateur":"internet","visite":"internet",
        "cherche":"internet","chercher":"internet","url":"internet",
        "click":"internet","clique":"internet","screenshot":"internet","capture":"internet",
        "telecharge":"internet","linkedin":"internet","google":"internet","youtube":"internet",
        "instagram":"internet","navigue":"internet",
        "page":"internet","contenu":"internet","lis-la":"internet","scrape":"internet",
        # cartes / images cherchees en ligne (pas des fichiers locaux)
        "carte":"internet","cartes":"internet","drapeau":"internet","drapeaux":"internet",
        # ouvrir = systeme (open_file) EN PRIORITÉ sur internet
        # L'utilisateur dit "ouvre" pour ouvrir un fichier/dossier local
        "ouvre":"systeme","ouvrir":"systeme","open":"systeme","va":"systeme","vas":"systeme",
        "lance":"systeme","lancer":"systeme","affiche":"systeme","afficher":"systeme",
        "editeur":"systeme","vscode":"systeme","notepad":"systeme","montre":"systeme",
        # email
        "email":"email","emails":"email","mail":"email","mails":"email","boite":"email",
        "envoie":"email","envoyer":"email","lis-mes":"email","dernier-email":"email",
        "send":"email","gmail":"email","message":"email","reponse":"email","repond":"email",
        "expediteur":"email","sujet":"email","piece":"email","jointe":"email",
        "inbox":"email","reception":"email","nouveau":"email","nouveaux":"email",
        "non-lu":"email","nonlu":"email",
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
        "screenshot-ecran":"media","capture-ecran":"media",
        # images
        "image":"images","images":"images","photo":"images","photos":"images",
        "redimensionne":"images","resize":"images","convertis-image":"images",
        "png":"images","jpg":"images","jpeg":"images","webp":"images","bmp":"images",
        # météo / info / traduction
        "meteo":"info","temps":"info","temperature":"info","previsions":"info",
        "traduis":"info","traduire":"info","traduction":"info","langue":"info",
        "translate":"info","stats":"info","statistiques":"info","version":"info",
        "licence":"info","mise-a-jour":"info","update":"info","pluie":"info","soleil":"info",
        # planificateur taches
        "planifie":"planif","planifier":"planif","tache":"planif","taches":"planif",
        "planificateur":"planif","cron":"planif","automatique":"planif","chaque":"planif",
        "quotidien":"planif","hebdo":"planif","programme":"planif",
        # hardware / parametres systeme (v1.4)
        "volume":"hardware","son":"hardware","audio":"hardware","muet":"hardware",
        "silence":"hardware","sourd":"hardware","bascule":"hardware",
        "lumiere":"hardware","luminosite":"hardware","lumineux":"hardware",
        "sombre":"hardware","clarte":"hardware","eclairer":"hardware","assombrir":"hardware",
        "wifi":"hardware","wi-fi":"hardware","sans-fil":"hardware","wlan":"hardware",
        "bluetooth":"hardware","reseau-wifi":"hardware",
        # vision ecran (v1.4+)
        "vois-ecran":"vision","regarde-ecran":"vision","observe":"vision",
        "analyse-mon-ecran":"vision","que-vois-tu":"vision","vision":"vision",
        "vois-tu":"vision","regardes":"vision","captur":"vision",
        # mots seuls ou paires qui signifient "regarde ce qui est sur l'ecran"
        "ecran":"vision","mon-ecran":"vision","sur-ecran":"vision",
        "l-ecran":"vision","lis-ecran":"vision","lire-ecran":"vision",
        "que-vois":"vision","regarde":"vision","vois":"vision",
        "lit-ecran":"vision","ecrat":"vision","quoi-sur":"vision",
        # youtube (v1.4)
        "youtube":"youtube","yt":"youtube","video":"youtube","videos":"youtube",
        "musique":"youtube","chanson":"youtube","chansons":"youtube",
        "film":"youtube","films":"youtube","serie":"youtube","clip":"youtube",
        # vols / voyages (v1.4)
        "vol":"flights","vols":"flights","avion":"flights","avions":"flights",
        "billet":"flights","aeroport":"flights","voyage":"flights","voyager":"flights",
        "depart":"flights","arrivee":"flights","aller":"flights","retour":"flights",
        "skyscanner":"flights","kayak":"flights","booking":"flights",
        # planification multi-etapes (v1.4)
        "plan":"planner","etapes":"planner","etape-par-etape":"planner",
        "objectif-complexe":"planner","fais-tout":"planner","execute-plan":"planner",
        "multi-etapes":"planner","sequence":"planner",
        # suppression fichier (v1.5)
        "supprime":"fichiers","supprimer":"fichiers","efface":"fichiers","effacer":"fichiers",
        "vide":"fichiers","retire":"fichiers","enleve":"fichiers","enlever":"fichiers",
        # résumé / analyse document (v1.5)
        "resume":"documents","resumer":"documents","resumé":"documents","synthese":"documents",
        "analyse":"documents","analyser":"documents","lis":"documents","explique-moi":"documents",
        # brouillon email (v1.5)
        "brouillon":"email","redige-email":"email","prépare-email":"email","draft":"email",
        # processus / kill (v1.5)
        "ferme":"systeme","tuer":"systeme","stoppe":"systeme","stopper":"systeme",
        "termine":"systeme","terminer":"systeme","quitte":"systeme","coupe":"systeme",
        "fige":"systeme","plante":"systeme","bloque":"systeme",
        # code (v1.5)
        "code":"code","coder":"code","programme":"code","programmer":"code",
        "script":"code","executer":"code","exécute":"code","exécuter":"code",
        "lancer-script":"code","lance-script":"code","python":"code","javascript":"code",
        "node":"code","debug":"code","debugue":"code","explique-code":"code",
        # musique (v1.5)
        "musique":"youtube","chanson":"youtube","chansons":"youtube","joue":"youtube",
        "jouer":"youtube","mets":"youtube","ecouter":"youtube","écoute":"youtube",
        "music":"youtube","song":"youtube","play":"youtube",
        # jeux Steam/Epic (v1.5)
        "steam":"jeux","epic":"jeux","epicgames":"jeux","jeu":"jeux","jeux":"jeux",
        "gamer":"jeux","videogame":"jeux","installe-jeu":"jeux","demarre-jeu":"jeux",
        # webcam (v1.5)
        "webcam":"webcam","camera":"webcam","cam":"webcam","auto-mute":"webcam",
        "automute":"webcam",
    }

    # Catégories → noms d'outils inclus
    _CAT_TOOLS = {
        "fichiers":  {"list_files","organize_folder","find_files","move_file","create_folder","read_file","write_file","edit_file","edit_pdf","get_folder_info","delete_file","summarize"},
        "documents": {"create_word","create_txt","create_pdf","read_document","write_file","edit_file","edit_pdf","summarize"},
        "internet":  {"web_search","read_webpage","open_browser","click_element","fill_form","take_screenshot","get_page_text","click_text","type_in_field"},
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
        # Nouveaux (v1.4)
        "hardware":  {"set_volume","get_audio_level","mute_audio","set_brightness","get_brightness","wifi_toggle"},
        "vision":    {"analyze_screen","screenshot_full"},
        "youtube":   {"open_youtube","search_youtube","play_music","open_browser","web_search"},
        "flights":   {"search_flights","web_search","open_browser"},
        "planner":   {"create_plan","execute_plan"},
        "jeux":      {"open_steam","open_epic_games","list_installed_steam_games",
                       "launch_game_steam","search_game_on_steam","install_game_steam"},
        "webcam":    {"analyze_webcam","start_auto_mute","stop_auto_mute"},
    }

    def _select_tools(self, message: str):
        """Retourne la sous-liste TOOLS_DEFINITIONS pertinente, ou None si pas d'outil."""
        import unicodedata
        # Supprime les accents pour que "météo" matche "meteo", "crée" → "cree", etc.
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

    def _groq_call(self, messages, tools=None, model_override=None):
        """Appel Groq via le client partage (rotation de cles + retry backoff geres
        de maniere centrale dans GroqClient — voir groq_client.py).
        model_override : force un modèle spécifique (ex: 8B pour questions simples)
        """
        return self.groq.chat(
            messages, model=model_override or MODEL, tools=tools,
            max_tokens=1024, temperature=0.4,
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
            response = self._groq_call(self.messages, tools=tools, model_override=active_model)
        except Exception as e:
            # Quand le modele tente d'appeler un outil hors de la sous-liste
            # ciblee, Groq rejette l'appel avec une erreur 400 AVANT meme de
            # renvoyer finish_reason="tool_calls" -- le filet ci-dessous ne
            # peut donc jamais s'en charger. On relance avec tous les outils
            # plutot que de remonter cette erreur a l'utilisateur.
            if "not in request.tools" in str(e):
                response = self._groq_call(self.messages, tools=TOOLS_DEFINITIONS,
                                           model_override=MODEL)
            else:
                raise

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
        tk.Label(hdr, text="v1.5.0  ·  87 outils  ·  Windows 11",
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
