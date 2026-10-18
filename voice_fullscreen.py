"""
Amah Agent — Interface Vocale Plein Écran
Style : HUD futuriste / cyberpunk (hexagone central, grille, coins HUD)
Lancement : py -3.13 voice_fullscreen.py
Quitter   : dire "ferme" / "quitte" / "au revoir"  ou  Échap
"""
import os, sys, json, math, random, time, threading, queue
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import tkinter as tk
from dotenv import load_dotenv

# ── Chargement .env ──────────────────────────────────────────────────────────
_env = (Path(sys.executable).parent / ".env"
        if getattr(sys, "frozen", False)
        else Path(__file__).parent / ".env")
load_dotenv(_env)
from tools.voice import speak
from tools import TOOL_FUNCTIONS
from tools.updater import CURRENT_VERSION
from tools.tool_router import select_tools, forced_tool
from tools.instant import instant_reply
from tools.guard import set_confirm_handler, tk_confirm_handler
from config import SYSTEM_PROMPT, TOOLS_DEFINITIONS, chat_messages
from groq_client import GroqClient, repair_tool_use_failed

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Pré-import pour que le premier F9 n'ait pas le délai d'import froid (~0.5s)
try:
    import gemini_client as _gemini_mod        # noqa: F401
except Exception:
    _gemini_mod = None

_LIVE_LOG = Path(__file__).parent / "live_debug.log"

def _log(msg):
    """Debug temporaire : trace le cycle de vie du Mode Live dans un fichier."""
    try:
        with open(_LIVE_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='milliseconds')} {msg}\n")
    except Exception:
        pass

# ── Palette cyberpunk / HUD ──────────────────────────────────────────────────
BG        = "#03050a"        # noir presque pur, légère teinte bleue
GRID      = "#0a1020"        # grille de fond
CYAN      = "#00d4ff"        # cyan électrique
CYAN_DIM  = "#003845"
GOLD      = "#c8a96e"        # or Amah
GOLD_DIM  = "#2a1f08"
GOLD_LT   = "#f0d090"
GREEN     = "#00ff88"        # vert néon
RED       = "#ff3355"        # rouge néon
WHITE     = "#e8f4ff"
DIM       = "#1a2535"
TEXT_BODY = "#a0c8e0"

LIVE_COLOR = "#b388ff"   # violet -- mode Live Gemini

def _reading_aloud() -> bool:
    """Une page est-elle en cours de lecture (outil read_aloud) ?"""
    reader = sys.modules.get("tools.reader")   # pas importé = rien n'est lu
    return reader is not None and reader.is_reading()


STATES = {
    "IDLE":   (CYAN_DIM,  "AMAH  ·  EN ATTENTE"),
    "ECOUTE": (CYAN,      "ECOUTE..."),
    "PENSE":  (GOLD,      "TRAITEMENT  ·  IA"),
    "REPOND": (GREEN,     "REPOND"),
    "ERREUR": (RED,       "ERREUR"),
    "LIVE":   (LIVE_COLOR,"MODE LIVE  ·  GEMINI"),
}

# Anneau de barres "vivant" autour de l'hexagone : (amplitude de base,
# amplitude de variation, vitesse) par etat -- inspire de la maquette
# idees/mockup_hud_voice.html (REPOS / ECOUTE / AMAH PARLE).
_RING_REACT = {
    "IDLE":   (0.05, 0.04, 1.0),
    "ECOUTE": (0.20, 0.30, 2.5),
    "PENSE":  (0.18, 0.18, 1.8),
    "REPOND": (0.40, 0.55, 5.0),
    "ERREUR": (0.06, 0.04, 1.0),
    "LIVE":   (0.40, 0.55, 5.0),
}

STOP_WORDS = {
    "ferme","quitte","quitter","stop","au revoir","aurevoir",
    "goodbye","bye","exit","close","arrete","arrête",
}

MODEL_FAST  = "openai/gpt-oss-20b"       # questions simples sans outils (~300ms)
MODEL_FULL  = "openai/gpt-oss-120b"      # requêtes avec outils (~1-2s)

# ── Routeur d'outils : tools/tool_router.py (partagé avec gui.py et agent.py) ──

# Outil local (hors TOOLS_DEFINITIONS) : bascule du Mode Live Gemini, gere
# directement par cette interface (F9). Ajoute a chaque appel pour qu'Amah
# puisse l'activer/desactiver a la demande, sans passer par le clavier.
_LIVE_TOOL = {
    "type": "function",
    "function": {
        "name": "toggle_live_mode",
        "description": ("Active ou desactive le Mode Live : conversation audio en "
                         "temps reel avec Gemini (comme un appel), avec interruption "
                         "naturelle. A utiliser seulement si l'utilisateur demande "
                         "explicitement de passer en mode live / conversation directe, "
                         "ou d'en sortir."),
        "parameters": {
            "type": "object",
            "properties": {
                "activer": {"type": "boolean",
                             "description": "true pour activer le Mode Live, false pour le desactiver."},
            },
            "required": ["activer"],
        },
    },
}

# Outil local : affiche/masque l'apercu webcam en direct dans le HUD
# (Ctrl+W). Pas un appel d'analyse IA -- juste l'image en continu a l'ecran.
_WEBCAM_PREVIEW_TOOL = {
    "type": "function",
    "function": {
        "name": "toggle_webcam_preview",
        "description": ("Affiche ou masque l'apercu video de la webcam en "
                         "direct dans le coin de l'interface vocale (pas "
                         "d'analyse IA, juste l'image). A utiliser si "
                         "l'utilisateur demande de voir/afficher/montrer la "
                         "webcam en direct, ou de la cacher/fermer."),
        "parameters": {
            "type": "object",
            "properties": {
                "activer": {"type": "boolean",
                             "description": "true pour afficher l'apercu, false pour le masquer."},
            },
            "required": ["activer"],
        },
    },
}

# Outil local : affiche/masque le champ de saisie texte (Ctrl+T). Permet a
# l'utilisateur de demander vocalement "ouvre le champ texte" sans toucher au clavier.
_TEXT_ENTRY_TOOL = {
    "type": "function",
    "function": {
        "name": "toggle_text_entry",
        "description": ("Affiche ou masque un petit champ de saisie texte dans "
                         "l'interface vocale, pour ecrire un message au lieu de "
                         "parler. A utiliser si l'utilisateur demande d'afficher/"
                         "ouvrir/montrer le champ ou la zone de texte, ou de le "
                         "fermer/masquer."),
        "parameters": {
            "type": "object",
            "properties": {
                "activer": {"type": "boolean",
                             "description": "true pour afficher le champ, false pour le masquer."},
            },
            "required": ["activer"],
        },
    },
}

def _select_tools(message: str):
    """Outils du routeur partagé + outils locaux de l'interface vocale.
    Conversation pure -> [] : réponse rapide par MODEL_FAST, sans outil."""
    tools, _info = select_tools(message, TOOLS_DEFINITIONS)
    if not tools:
        return []
    return tools + [_LIVE_TOOL, _WEBCAM_PREVIEW_TOOL, _TEXT_ENTRY_TOOL]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    r1,g1,b1 = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t))

def _hex_points(cx, cy, r, angle_offset=0):
    """Retourne les 6 sommets d'un hexagone régulier."""
    pts = []
    for i in range(6):
        a = math.radians(60 * i + angle_offset)
        pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return pts


# ── TTS local instantané (pyttsx3, sans réseau) ──────────────────────────────

class _TtsWorker:
    """Synthèse vocale locale via pyttsx3 (SAPI5 Windows).
    Thread dédié — aucun appel réseau, audio démarre en < 50ms."""

    def __init__(self):
        self._queue     = queue.Queue()
        self._done      = threading.Event()
        self._done.set()
        self._engine    = None
        self._available = False
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 165)
            for v in engine.getProperty('voices'):
                if any(k in v.id.lower() for k in ('fr', 'hortense', 'julie')):
                    engine.setProperty('voice', v.id)
                    break
            self._engine    = engine
            self._available = True
        except Exception:
            return
        while True:
            text = self._queue.get()
            if text is None:
                break
            if not text.strip():
                self._done.set()
                continue
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                pass
            self._done.set()

    def say(self, text: str) -> dict:
        """Parle le texte (bloquant). Repli sur edge-tts si pyttsx3 indisponible."""
        if not self._available:
            return speak(text)
        self._done.clear()
        self._queue.put(text)
        self._done.wait(timeout=60)
        return {"success": True}

    def stop(self):
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass


# ── Interface ─────────────────────────────────────────────────────────────────

class AmahVoiceUI:

    def __init__(self):
        try:
            self.client = GroqClient.get()
        except RuntimeError as e:
            raise SystemExit(str(e))
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        self.state    = "IDLE"
        self._frame   = 0
        self._running = True
        self._color   = CYAN_DIM
        self._label   = STATES["IDLE"][1]
        self._mic_ready = False   # True une fois le micro calibré
        self._mic_error = ""      # raison de l'échec d'init, affichée à l'utilisateur
        self._sr = None
        self._mic = None
        self._listening_active = threading.Event()  # micro Groq ouvert (with self._mic)

        self._live_mode    = False  # True pendant le mode Live (Gemini, audio temps reel)
        self._live_session = None
        self._pending_live_action = None  # "start"/"stop" : applique apres la confirmation vocale

        self._webcam_active = threading.Event()  # apercu webcam en direct dans le HUD
        self._webcam_frame  = None                # derniere image PIL (thread camera)
        self._webcam_photo  = None                # PhotoImage Tk (cree dans le thread UI)

        self._tts = _TtsWorker()   # TTS local instantané (pyttsx3, thread dédié)
        self._chat_lock = threading.Lock()  # serialise _chat() entre voix et texte tape
        self._text_entry_visible = False  # suivi thread-safe (winfo_ismapped n'est pas thread-safe)

        self._cpu = 0.0   # % CPU, mis a jour par _metrics_loop (jauges bas-gauche)
        self._ram = 0.0   # % RAM
        self._recent_memories = []  # derniers contenus get_memories (panneau bas-droite)

        self._build()
        self._grid_img = self._make_grid(self._W, self._H)  # grille pré-rendue 1×
        self._animate()
        threading.Thread(target=self._init_mic, daemon=True).start()
        threading.Thread(target=self._metrics_loop, daemon=True).start()
        threading.Thread(target=self._memories_loop, daemon=True).start()
        self.root.after(1800, self._start_loop)

    # ── Construction ─────────────────────────────────────────────────────────

    def _build(self):
        self.root = tk.Tk()
        # Actions sensibles (mode normal et mode Live) : boite Oui/Non
        set_confirm_handler(tk_confirm_handler(self.root))
        self.root.title("Amah — Interface Vocale")
        self.root.configure(bg=BG)
        self.root.attributes("-fullscreen", True)
        # Lancee depuis amah_listener.py (processus en arriere-plan), la fenetre
        # est creee sans le style WS_VISIBLE : Windows ne l'affiche jamais sans
        # deiconify(), meme avec "-topmost". On la passe ensuite au premier plan
        # avec lift()/focus_force() (anti focus-stealing) ; "-topmost" est retire
        # apres coup pour ne pas la geler au-dessus de tout en permanence.
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()
        self.root.after(300, lambda: self.root.attributes("-topmost", False))
        self.root.bind("<Escape>", lambda e: self._on_escape())
        self.root.bind("<F11>",    lambda e: self._toggle_fs())
        self.root.bind("<F9>",     lambda e: self._toggle_live())
        # F9 est souvent une touche multimedia (volume/luminosite) sur les
        # claviers de portable et necessite Fn -- on ajoute un raccourci
        # de secours qui n'a pas ce probleme.
        self.root.bind("<Control-l>", lambda e: self._toggle_live())
        self.root.bind("<Control-w>", lambda e: self._toggle_webcam_preview())
        self.root.bind("<Control-t>", lambda e: self._toggle_text_entry())

        W = self.root.winfo_screenwidth()
        H = self.root.winfo_screenheight()
        self._W, self._H = W, H
        self._cx = W // 2
        self._cy = int(H * 0.42)

        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.canvas.place(x=0, y=0, width=W, height=H)

        # Transcript utilisateur
        self._user_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self._user_var,
                 bg=BG, fg=CYAN_DIM, font=("Consolas", 13, "italic"),
                 wraplength=int(W * 0.65), justify="center",
                 ).place(relx=0.5, rely=0.73, anchor="center")

        # Réponse Amah
        self._reply_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self._reply_var,
                 bg=BG, fg=TEXT_BODY, font=("Consolas", 17),
                 wraplength=int(W * 0.72), justify="center",
                 ).place(relx=0.5, rely=0.84, anchor="center")

        # Hint bas
        tk.Label(self.root,
                 text='Dire  "ferme"  ou  Échap  pour quitter   ·   F11 plein écran   ·   F9 / Ctrl+L mode Live (Gemini)   ·   Ctrl+W webcam en direct   ·   Ctrl+T champ texte',
                 bg=BG, fg=DIM, font=("Consolas", 9),
                 ).place(relx=0.5, rely=0.97, anchor="center")

        # Champ de saisie texte (masqué par défaut, Ctrl+T pour l'afficher) --
        # fonctionne en mode normal (Groq) comme en Mode Live (Gemini).
        self._text_var = tk.StringVar(value="")
        self._text_entry = tk.Entry(
            self.root, textvariable=self._text_var,
            bg=_blend(BG, CYAN, 0.10), fg=WHITE, insertbackground=CYAN,
            font=("Consolas", 13), relief="flat",
            highlightthickness=2, highlightbackground=CYAN, highlightcolor=CYAN,
        )
        self._text_entry.bind("<Return>", self._submit_text)
        self._text_entry.bind("<Escape>", self._hide_text_entry)

    # ── Animation ─────────────────────────────────────────────────────────────

    def _animate(self):
        if not self._running:
            return
        self._frame += 1
        self._draw()
        self.root.after(40, self._animate)   # 25 fps

    def _draw(self):
        c       = self.canvas
        f       = self._frame
        W, H    = self._W, self._H
        cx, cy  = self._cx, self._cy
        color   = self._color
        c.delete("all")

        # ── Fond : grille hexagonale subtile ──────────────────────────────
        self._draw_grid(c, W, H, color)

        # ── Lignes de scan (sweep) ────────────────────────────────────────
        for offset in (0, 180):
            scan = math.radians(f * 2.5 + offset)
            c.create_line(cx, cy,
                          cx + 320 * math.cos(scan),
                          cy + 320 * math.sin(scan),
                          fill=_blend(BG, color, 0.25), width=1, dash=(4, 12))

        # ── Cercles concentriques dégradés ────────────────────────────────
        for r, a in [(300, 0.04), (230, 0.07), (170, 0.11), (120, 0.15), (80, 0.20)]:
            fill = _blend(BG, color, a)
            c.create_oval(cx-r, cy-r, cx+r, cy+r, fill=fill, outline="")

        # ── Anneau extérieur rotatif (24 points) ──────────────────────────
        r_out = 250
        for i in range(24):
            ang    = math.radians(f * 1.5 + i * 15)
            px     = cx + r_out * math.cos(ang)
            py     = cy + r_out * math.sin(ang)
            bright = 0.10 + 0.90 * (0.5 + 0.5 * math.sin(math.radians(f * 6 + i * 15)))
            col    = _blend(DIM, color, bright)
            size   = 3 if i % 6 == 0 else 2
            c.create_oval(px-size, py-size, px+size, py+size, fill=col, outline="")

        # ── Anneau intermédiaire contra-rotatif (tirets) ──────────────────
        r_mid = 188
        for i in range(16):
            ang = math.radians(-f * 1.2 + i * 22.5)
            x1 = cx + (r_mid - 16) * math.cos(ang)
            y1 = cy + (r_mid - 16) * math.sin(ang)
            x2 = cx + (r_mid + 16) * math.cos(ang)
            y2 = cy + (r_mid + 16) * math.sin(ang)
            c.create_line(x1, y1, x2, y2,
                          fill=_blend(DIM, color, 0.6), width=2)

        # ── Anneau de barres "vivant", reactif a l'etat ────────────────────
        # Inspire de idees/mockup_hud_voice.html : les batons partent du bord
        # de l'anneau exterieur (r_out) et grandissent vers l'exterieur, avec
        # une amplitude/vivacite qui depend de l'etat (repos/ecoute/parle).
        amp_base, amp_jit, speed = _RING_REACT.get(self.state, _RING_REACT["IDLE"])
        n_bars = 48
        for i in range(n_bars):
            ang   = math.radians(i * (360 / n_bars))
            wave  = 0.5 + 0.5 * math.sin(math.radians(f * speed * 3 + i * 7.5))
            noise = random.random()
            amp   = amp_base + amp_jit * (0.6 * wave + 0.4 * noise)
            length = 6 + amp * 35
            x1 = cx + r_out * math.cos(ang)
            y1 = cy + r_out * math.sin(ang)
            x2 = cx + (r_out + length) * math.cos(ang)
            y2 = cy + (r_out + length) * math.sin(ang)
            bcol = _blend(BG, color, 0.20 + amp * 0.80)
            c.create_line(x1, y1, x2, y2, fill=bcol, width=3)

        # ── Anneau pulsant ────────────────────────────────────────────────
        pulse = 128 + 12 * math.sin(math.radians(f * 4))
        c.create_oval(cx-pulse, cy-pulse, cx+pulse, cy+pulse,
                      outline=color, width=1)

        # ── Hexagone central rotatif ──────────────────────────────────────
        hex_r = 88 + 6 * math.sin(math.radians(f * 5))
        pts   = _hex_points(cx, cy, hex_r, angle_offset=f * 0.6)
        c.create_polygon(pts, outline=color, fill=_blend(BG, color, 0.08), width=2)

        # Hexagone intérieur contra-rotatif
        hex_r2 = 62
        pts2   = _hex_points(cx, cy, hex_r2, angle_offset=-f * 0.9 + 30)
        c.create_polygon(pts2, outline=_blend(BG, color, 0.5),
                         fill="", width=1)

        # ── Orbe central ──────────────────────────────────────────────────
        orb = 42 + 4 * math.sin(math.radians(f * 7))
        c.create_oval(cx-orb, cy-orb, cx+orb, cy+orb,
                      fill=_blend(BG, color, 0.12), outline=color, width=2)

        # Lettre "A" stylisée
        c.create_text(cx, cy, text="A",
                      fill=color, font=("Consolas", 40, "bold"))

        # Croix HUD
        arm = 20
        c.create_line(cx-arm, cy, cx+arm, cy, fill=color, width=1)
        c.create_line(cx, cy-arm, cx, cy+arm, fill=color, width=1)

        # ── Label état ────────────────────────────────────────────────────
        c.create_text(cx, cy + 165, text=self._label,
                      fill=color, font=("Consolas", 15, "bold"))

        # ── Barres audio animées ──────────────────────────────────────────
        if self.state in ("ECOUTE", "REPOND", "LIVE"):
            n, sp = 36, 12
            x0    = cx - (n * sp) // 2
            y_mid = cy + 215
            for i in range(n):
                h_b = 4 + 28 * abs(math.sin(math.radians(f * 9 + i * 14)))
                x   = x0 + i * sp
                col = GOLD_LT if i % 3 == 0 else color
                c.create_rectangle(x, y_mid - h_b, x + 8, y_mid + h_b,
                                   fill=col, outline="")

        # ── Coins HUD ─────────────────────────────────────────────────────
        self._draw_corners(c, W, H, color)

        # ── En-tête ───────────────────────────────────────────────────────
        c.create_text(40, 28, text=f"AMAH  AGENT  v{CURRENT_VERSION}",
                      fill=color, font=("Consolas", 11, "bold"), anchor="nw")
        c.create_text(40, 48, text="INTERFACE VOCALE  ·  GROQ AI",
                      fill=_blend(BG, color, 0.45),
                      font=("Consolas", 9), anchor="nw")

        # Heure
        now = datetime.now().strftime("%H:%M:%S")
        c.create_text(W - 40, 28, text=now,
                      fill=color, font=("Consolas", 14, "bold"), anchor="ne")
        c.create_text(W - 40, 48,
                      text=datetime.now().strftime("%a %d %b %Y"),
                      fill=_blend(BG, color, 0.45),
                      font=("Consolas", 9), anchor="ne")
        c.create_line(W - 22, 14, W - 22, 60, fill=color, width=2)

        # ── Jauges CPU / RAM (bas gauche) ──────────────────────────────────
        c.create_line(22, H - 116, 22, H - 56, fill=color, width=2)
        bx, by = 46, H - 100
        for jlabel, val in (("CPU", self._cpu), ("RAM", self._ram)):
            c.create_text(bx, by, text=jlabel, fill=_blend(BG, color, 0.6),
                          font=("Consolas", 10, "bold"), anchor="w")
            track_x, track_w = bx + 50, 140
            c.create_rectangle(track_x, by - 6, track_x + track_w, by + 6,
                               outline=_blend(BG, color, 0.4))
            fill_w = track_w * max(0.0, min(100.0, val)) / 100.0
            bar_col = RED if val >= 85 else (GOLD if val >= 65 else color)
            if fill_w > 0:
                c.create_rectangle(track_x, by - 6, track_x + fill_w, by + 6,
                                   fill=bar_col, outline="")
            c.create_text(track_x + track_w + 10, by, text=f"{val:.0f}%",
                          fill=_blend(BG, color, 0.6), font=("Consolas", 10), anchor="w")
            by += 26

        # ── Dernieres memoires enregistrees (bas droite) ───────────────────
        # Place au-dessus du widget "Amah ecoute" (amah_listener.py, ~80px,
        # coin bas-droit) pour eviter tout chevauchement.
        my = H - 220
        c.create_line(W - 22, my - 26, W - 22, my + 64, fill=color, width=2)
        c.create_text(W - 40, my, text="MEMOIRE", fill=color,
                      font=("Consolas", 10, "bold"), anchor="e")
        if self._recent_memories:
            for mem in self._recent_memories[:3]:
                my += 20
                txt = mem if len(mem) <= 42 else mem[:41] + "…"
                c.create_text(W - 40, my, text=txt, fill=_blend(BG, color, 0.6),
                              font=("Consolas", 9), anchor="e")
        else:
            my += 20
            c.create_text(W - 40, my, text="(aucune memoire enregistree)",
                          fill=_blend(BG, color, 0.4),
                          font=("Consolas", 9), anchor="e")

        # ── Champ de saisie texte (Ctrl+T) ─────────────────────────────────
        # Cadre + etiquette autour du tk.Entry place par _toggle_text_entry,
        # pour le rendre clairement visible (fond sombre sinon peu contraste).
        if self._text_entry_visible:
            ex1, ex2 = W * 0.25, W * 0.75
            ey1, ey2 = H * 0.91 - 17, H * 0.91 + 17
            c.create_rectangle(ex1 - 4, ey1 - 4, ex2 + 4, ey2 + 4,
                               outline=color, width=2)
            c.create_text((ex1 + ex2) / 2, ey1 - 16,
                          text="CHAMP TEXTE — Entree pour envoyer · Echap pour fermer",
                          fill=color, font=("Consolas", 9, "bold"))

        # ── Apercu webcam en direct (Ctrl+W) ───────────────────────────────
        if self._webcam_active.is_set() and self._webcam_frame is not None:
            from PIL import ImageTk
            self._webcam_photo = ImageTk.PhotoImage(self._webcam_frame)
            pw, ph = self._webcam_photo.width(), self._webcam_photo.height()
            x2, y1 = W - 18, 70
            x1, y2 = x2 - pw, y1 + ph
            c.create_image(x2, y1, anchor="ne", image=self._webcam_photo)
            c.create_rectangle(x1, y1, x2, y2, outline=color, width=1)
            c.create_text(x2 - 6, y2 + 12, text="WEBCAM · EN DIRECT",
                          fill=color, font=("Consolas", 9, "bold"), anchor="ne")

    def _make_grid(self, W, H):
        """Pré-rend la grille de points une seule fois en image PIL → PhotoImage."""
        try:
            from PIL import Image, ImageDraw, ImageTk
            img  = Image.new("RGB", (W, H), BG)
            draw = ImageDraw.Draw(img)
            step = 56
            dot  = _blend(BG, CYAN_DIM, 0.4)
            dc   = (int(dot[1:3],16), int(dot[3:5],16), int(dot[5:7],16))
            for x in range(0, W, step):
                for y in range(0, H, step):
                    draw.ellipse([x-1, y-1, x+1, y+1], fill=dc)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None   # PIL indisponible — on s'en passe

    def _draw_grid(self, c, W, H, color):
        """Tampon image pré-rendue — 1 seule opération par frame."""
        if self._grid_img:
            c.create_image(0, 0, anchor="nw", image=self._grid_img)

    def _draw_corners(self, c, W, H, color):
        """Décorations HUD dans les 4 coins."""
        L = 32   # longueur du bras
        T = 2    # épaisseur
        P = 18   # marge
        col = _blend(BG, color, 0.7)
        # Coin haut-gauche
        c.create_line(P,   P,   P+L, P,   fill=col, width=T)
        c.create_line(P,   P,   P,   P+L, fill=col, width=T)
        # Coin haut-droit
        c.create_line(W-P, P,   W-P-L, P,   fill=col, width=T)
        c.create_line(W-P, P,   W-P,   P+L, fill=col, width=T)
        # Coin bas-gauche
        c.create_line(P,   H-P, P+L,   H-P, fill=col, width=T)
        c.create_line(P,   H-P, P,     H-P-L, fill=col, width=T)
        # Coin bas-droit
        c.create_line(W-P, H-P, W-P-L, H-P, fill=col, width=T)
        c.create_line(W-P, H-P, W-P,   H-P-L, fill=col, width=T)

    # ── Conversation ─────────────────────────────────────────────────────────

    def _set_state(self, state, user="", reply="", label=None):
        self.state  = state
        self._color = STATES[state][0]
        self._label = label if label is not None else STATES[state][1]
        self._user_var.set(user)
        self._reply_var.set(reply)

    def _init_mic(self):
        """Crée Recognizer + Microphone une seule fois et calibre."""
        try:
            import speech_recognition as sr
            self._sr = sr.Recognizer()
            self._sr.pause_threshold          = 0.6
            self._sr.energy_threshold         = 200
            self._sr.dynamic_energy_threshold = False  # evite que le seuil monte trop haut sur bruit de fond
            self._mic = sr.Microphone()
            with self._mic as src:
                self._sr.adjust_for_ambient_noise(src, duration=0.5)
            self._mic_ready = True
        except Exception as e:
            self._mic_ready = False
            self._mic_error = str(e)

    def _metrics_loop(self):
        """Met a jour self._cpu/self._ram toutes les 2s (jauges bas-gauche)."""
        try:
            import psutil
        except ImportError:
            return
        while self._running:
            try:
                self._cpu = psutil.cpu_percent(interval=1)
                self._ram = psutil.virtual_memory().percent
            except Exception:
                time.sleep(2)

    def _memories_loop(self):
        """Recharge les dernieres memoires enregistrees toutes les 30s
        (panneau bas-droite)."""
        from tools.memory import get_memories
        while self._running:
            try:
                res = get_memories()
                if res.get("success"):
                    self._recent_memories = [m["contenu"] for m in res.get("memories", [])[:3]]
            except Exception:
                pass
            for _ in range(30):
                if not self._running:
                    return
                time.sleep(1)

    def _listen_once(self):
        """Écoute une phrase (max 6s). Retourne le texte ou None."""
        if not self._mic_ready or self._sr is None:
            time.sleep(0.5)
            return None
        import speech_recognition as sr
        self._listening_active.set()
        try:
            with self._mic as src:
                audio = self._sr.listen(src, timeout=5, phrase_time_limit=6)
        except sr.WaitTimeoutError:
            return None   # rien dit dans le délai imparti
        finally:
            self._listening_active.clear()
        try:
            return self._sr.recognize_google(audio, language="fr-FR")
        except sr.UnknownValueError:
            return None   # parole incomprise
        except sr.RequestError:
            # Coupure DNS/reseau passagere (getaddrinfo failed...) : on retente
            # une fois avant de signaler une vraie panne a l'utilisateur.
            try:
                return self._sr.recognize_google(audio, language="fr-FR")
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                self.root.after(0, self._set_state, "ERREUR", "",
                                f"Reconnaissance vocale indisponible : {str(e)[:120]}")
                time.sleep(2.0)
                return None

    def _start_loop(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        # Attendre que le micro soit prêt
        deadline = time.time() + 8
        while not self._mic_ready and time.time() < deadline:
            time.sleep(0.3)

        if not self._mic_ready:
            detail = f" : {self._mic_error[:120]}" if self._mic_error else ""
            self.root.after(0, self._set_state, "ERREUR", "",
                            f"Micro indisponible{detail}")
            return

        self.root.after(0, self._set_state, "ECOUTE")
        was_reading = False
        while self._running:
            if self._live_mode:
                time.sleep(0.2)
                continue

            # Lecture d'une page à voix haute (read_aloud) : le micro
            # entendrait Amah et prendrait sa voix pour une demande
            if _reading_aloud():
                if not was_reading:
                    was_reading = True
                    self.root.after(0, self._set_state, "REPOND", "", "",
                                    "LECTURE  ·  ÉCHAP POUR ARRÊTER")
                time.sleep(0.3)
                continue
            if was_reading:
                was_reading = False
                self.root.after(0, self._set_state, "ECOUTE")

            texte = self._listen_once()
            if not texte:
                continue

            self._process_user_text(texte.strip())

    def _process_user_text(self, texte: str):
        """Traite un message (venant de la voix ou du champ texte) : appel
        Groq + reponse parlee/affichee. Peut etre appele depuis _loop ou
        depuis un thread declenche par la saisie texte (Ctrl+T)."""
        # Fermeture vocale
        if any(w in texte.lower() for w in STOP_WORDS):
            self.root.after(0, self._set_state, "IDLE", texte, "À bientôt.")
            self._tts.say("À bientôt.")
            time.sleep(0.3)
            self.root.after(0, self._quit)
            return

        # Traitement
        self.root.after(0, self._set_state, "PENSE", f'« {texte} »', "")
        with self._chat_lock:
            reply, is_err = self._chat(texte)

        if self._pending_live_action:
            # toggle_live_mode a ete demande : on parle la confirmation
            # D'ABORD (SAPI), puis on bascule _start_live/_stop_live --
            # sinon la synthese vocale et les flux audio Gemini
            # (sounddevice) s'ouvrent en meme temps sur les memes
            # peripheriques, ce qui fait planter la session Live juste
            # apres son activation.
            action = self._pending_live_action
            self._pending_live_action = None
            # Pose le flag tout de suite (synchrone, dans ce thread) -- sinon
            # _loop revient en haut de sa boucle pendant que _start_live est
            # seulement planifie via root.after (asynchrone, thread Tk) et
            # rouvre le micro Groq juste avant que Gemini ouvre le sien :
            # les deux flux audio se retrouvent ouverts en meme temps sur le
            # meme peripherique.
            self._live_mode = (action == "start")
            if reply and not is_err:
                self._tts.say(reply[:450])
            # Efface un eventuel message de statut Groq (rotation de cle)
            # laisse par _on_status pendant ce dernier echange.
            self.root.after(0, self._user_var.set, "")
            self.root.after(0, self._reply_var.set, "")
            if action == "start":
                self.root.after(0, self._start_live)
            else:
                self.root.after(0, self._stop_live)
            return

        short = reply if len(reply) <= 220 else reply[:217] + "…"
        if is_err:
            self.root.after(0, self._set_state, "ERREUR", f'« {texte} »', short)
            time.sleep(2.5)
        else:
            self.root.after(0, self._set_state, "REPOND", f'« {texte} »', short)
            # speak() est bloquant : on attend la fin réelle de la voix
            # au lieu d'estimer une durée, et on affiche l'erreur si la
            # synthèse échoue plutôt que de l'avaler en silence.
            # Pendant une lecture à voix haute : réponse affichée seulement,
            # sinon les deux voix parlent en même temps.
            voice_res = {} if _reading_aloud() else self._tts.say(reply[:450])
            if "error" in voice_res:
                self.root.after(0, self._set_state, "ERREUR", f'« {texte} »',
                                f"Voix indisponible : {voice_res['error'][:120]}")
                time.sleep(1.5)

        if self._running:
            self.root.after(0, self._set_state, "ECOUTE")

    def _chat(self, text: str):
        """Retourne (reply: str, is_error: bool)."""
        self.messages.append({"role": "user", "content": text})
        if len(self.messages) > 22:
            self.messages = [self.messages[0]] + self.messages[-20:]

        # Heure, date, calcul simple : réponse immédiate sans appel IA
        instant = instant_reply(text)
        if instant:
            self.messages.append({"role": "assistant", "content": instant})
            return instant, False

        tools = _select_tools(text)
        model = MODEL_FULL if tools else MODEL_FAST
        # Outil imposé au premier appel seulement : actualité -> web_search,
        # "lis cette page à voix haute" -> read_aloud (comme gui.py et agent.py)
        forced = forced_tool(text, tools) if tools else None
        pending_choice = [{"type": "function", "function": {"name": forced}}] if forced else []

        def _on_status(txt):
            # Affiche les messages de rotation/attente (limite Groq) dans la
            # zone de reponse au lieu de laisser l'ecran fige sur "TRAITEMENT".
            self.root.after(0, self._reply_var.set, txt)

        def _call(msgs, tl):
            return self.client.chat(
                messages=msgs, model=model, tools=tl,
                tool_choice=pending_choice.pop() if pending_choice else None,
                max_tokens=4096, temperature=0.4,
                on_status=_on_status,
            )

        def _call_safe(msgs):
            # Si le modele tente d'appeler un outil hors de la sous-liste
            # ciblee, Groq rejette avec une erreur 400 : on relance avec
            # tous les outils plutot que de remonter l'erreur.
            nonlocal tools
            try:
                return _call(msgs, tools)
            except Exception as e:
                if "not in request.tools" in str(e) and tools is not TOOLS_DEFINITIONS:
                    # Ajoute uniquement l'outil manquant au lieu des 99
                    repaired_name = repair_tool_use_failed(e)
                    if repaired_name:
                        missing_name = repaired_name[0]
                        extra = [t for t in TOOLS_DEFINITIONS
                                 if t["function"]["name"] == missing_name]
                        tools = list(tools) + extra
                    else:
                        tools = TOOLS_DEFINITIONS
                    return _call(msgs, tools)

                # Autre cas de 400 AVANT reponse : le modele a emis un appel
                # d'outil malforme en texte brut (tool_use_failed). On execute
                # quand meme l'outil reconstitue plutot que de remonter l'erreur.
                repaired = repair_tool_use_failed(e)
                if repaired is None:
                    raise
                name, args = repaired
                tc = SimpleNamespace(id="call_fixed",
                                      function=SimpleNamespace(name=name, arguments=json.dumps(args, ensure_ascii=False)))
                msgs.append({
                    "role":    "assistant",
                    "content": "",
                    "tool_calls": [{"id": tc.id, "type": "function",
                                    "function": {"name": name, "arguments": tc.function.arguments}}],
                })
                res = self._run_tool(tc, on_status=_on_status)
                msgs.append({"role": "tool", "tool_call_id": tc.id, "content": res})
                # Ajoute l'outil réparé à la liste courante au lieu des 99
                extra = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] == name]
                tools = list(tools) + [e for e in extra if e not in tools]
                return _call(msgs, tools)

        try:
            # Conversation pure (aucun outil) : prompt court, ~20x moins de tokens
            resp = _call_safe(self.messages if tools else chat_messages(self.messages))
            while resp.choices[0].finish_reason == "tool_calls":
                msg = resp.choices[0].message
                self.messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.function.name,
                                      "arguments": tc.function.arguments}}
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    res = self._run_tool(tc, on_status=_on_status)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": res,
                    })
                resp = _call_safe(self.messages)

            # Cas particulier : outil émis en texte brut <function>nom</function>{args}
            import re as _re
            _raw = resp.choices[0].message.content or ""
            _m = _re.match(
                r'^<function>([\w]+)</function>\s*(\{.*\})\s*$',
                _raw.strip(), _re.DOTALL
            )
            if _m:
                _tname, _targs = _m.group(1), _m.group(2)
                try:
                    _fake = SimpleNamespace(
                        id="txt-repair-0",
                        function=SimpleNamespace(name=_tname, arguments=_targs),
                    )
                    _res = self._run_tool(_fake, on_status=_on_status)
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
                    resp = _call_safe(self.messages)
                except Exception:
                    pass

            reply = resp.choices[0].message.content or "Compris."
            self.messages.append({"role": "assistant", "content": reply})
            return reply, False
        except Exception as e:
            return f"Erreur API : {e}", True

    def _run_tool(self, tc, on_status=None) -> str:
        try:
            args = json.loads(tc.function.arguments) or {}
        except Exception:
            args = {}

        if tc.function.name == "toggle_live_mode":
            return self._tool_toggle_live(args)

        if tc.function.name == "toggle_webcam_preview":
            return self._tool_toggle_webcam_preview(args)

        if tc.function.name == "toggle_text_entry":
            return self._tool_toggle_text_entry(args)

        func = TOOL_FUNCTIONS.get(tc.function.name)
        if not func:
            return json.dumps({"error": f"Outil inconnu: {tc.function.name}"})
        try:
            if tc.function.name == "execute_plan" and on_status:
                args["on_status"] = on_status
            return json.dumps(func(**args), ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _tool_toggle_live(self, args) -> str:
        # La bascule reelle (_start_live/_stop_live) est appliquee par _loop
        # APRES la confirmation vocale (speak), pour eviter que la synthese
        # SAPI et les flux audio Gemini (sounddevice) ne s'ouvrent en meme
        # temps sur les memes peripheriques.
        activer = args.get("activer", True)
        if activer:
            if self._live_mode:
                return json.dumps({"info": "Le mode Live est deja actif."}, ensure_ascii=False)
            if not GEMINI_API_KEY:
                return json.dumps({"error": "Mode Live indisponible : cle GEMINI_API_KEY manquante dans .env"}, ensure_ascii=False)
            self._pending_live_action = "start"
            return json.dumps({"success": True, "message": "Mode Live (Gemini) en cours d'activation."}, ensure_ascii=False)
        else:
            if not self._live_mode:
                return json.dumps({"info": "Le mode Live n'est pas actif."}, ensure_ascii=False)
            self._pending_live_action = "stop"
            return json.dumps({"success": True, "message": "Mode Live desactive, retour au mode normal."}, ensure_ascii=False)

    def _tool_toggle_webcam_preview(self, args) -> str:
        activer = bool(args.get("activer", True))
        if activer == self._webcam_active.is_set():
            etat = "deja affiche" if activer else "deja masque"
            return json.dumps({"info": f"Apercu webcam {etat}."}, ensure_ascii=False)
        self.root.after(0, self._toggle_webcam_preview)
        etat = "affiche" if activer else "masque"
        return json.dumps({"success": True, "message": f"Apercu webcam {etat}."}, ensure_ascii=False)

    def _tool_toggle_text_entry(self, args) -> str:
        activer = bool(args.get("activer", True))
        if activer == self._text_entry_visible:
            etat = "deja affiche" if activer else "deja masque"
            return json.dumps({"info": f"Champ texte {etat}."}, ensure_ascii=False)
        self.root.after(0, self._toggle_text_entry)
        etat = "affiche" if activer else "masque"
        return json.dumps({"success": True, "message": f"Champ texte {etat}."}, ensure_ascii=False)

    # ── Mode Live (Gemini, audio temps réel) ─────────────────────────────────

    def _toggle_live(self):
        if self._live_mode:
            self._stop_live()
        else:
            self._start_live()

    def _start_live(self):
        _log(f"_start_live appele (live_mode={self._live_mode})")
        if self._live_session is not None:
            return  # deja demarree (ex: _live_mode pose en avance par _process_user_text)
        if not GEMINI_API_KEY:
            self._live_mode = False
            self._set_state("ERREUR", "",
                            "Mode Live indisponible : GEMINI_API_KEY manquante dans .env")
            return
        try:
            from gemini_client import GeminiLiveSession
        except Exception as e:
            self._live_mode = False
            self._set_state("ERREUR", "", f"Module Gemini indisponible : {e}")
            return

        self._live_mode = True
        self._set_state("LIVE", "", "", label="MODE LIVE  ·  CONNEXION...")

        def _status(s):
            self.root.after(0, self._on_live_status, s)

        def _user_text(t):
            _log(f"_user_text: {t!r}")
            self.root.after(0, self._user_var.set, f'« {t} »')

        def _reply_text(t):
            _log(f"_reply_text: {t!r}")
            self.root.after(0, self._reply_var.set, t)

        def _tool(name, args, result):
            _log(f"_tool: {name} args={args!r}")
            self.root.after(0, self._reply_var.set, f"[outil] {name}…")

        self._live_session = GeminiLiveSession(
            api_key=GEMINI_API_KEY,
            on_status=_status,
            on_user_text=_user_text,
            on_reply_text=_reply_text,
            on_tool=_tool,
        )

        def _launch():
            # Attend que le micro Groq se libere avant d'ouvrir le flux Gemini
            deadline = time.time() + 2
            while self._listening_active.is_set() and time.time() < deadline:
                time.sleep(0.05)
            _log(f"_launch: demarrage GeminiLiveSession.start() "
                 f"(listening_active={self._listening_active.is_set()})")
            self._live_session.start()

        threading.Thread(target=_launch, daemon=True).start()

    def _on_live_status(self, status):
        _log(f"_on_live_status: live_mode={self._live_mode} status={status!r}")
        if not self._live_mode:
            return   # mode Live deja arrete -- on ignore les statuts tardifs
        if status.startswith("Erreur Live"):
            # Stoppe vraiment la session avant d'oublier la reference --
            # sinon le thread asyncio/sounddevice de Gemini continue de
            # tourner en arriere-plan (zombie) et entre en conflit avec le
            # micro de l'ecoute normale qui reprend juste apres.
            if self._live_session:
                self._live_session.stop()
            self._live_mode = False
            self._live_session = None
            self._set_state("ERREUR", "", status[:160])
            self.root.after(2000, lambda: self._set_state("ECOUTE"))
            return
        if status == "Session Live fermee":
            return
        self._color = LIVE_COLOR
        self._label = status
        self.state  = "LIVE"

    def _stop_live(self):
        if self._live_session:
            self._live_session.stop()
            self._live_session = None
        self._live_mode = False
        self._set_state("ECOUTE")

    # ── Apercu webcam en direct ──────────────────────────────────────────────

    def _toggle_webcam_preview(self):
        if self._webcam_active.is_set():
            self._webcam_active.clear()
            self._webcam_frame = None
            self._webcam_photo = None
        else:
            self._webcam_active.set()
            threading.Thread(target=self._webcam_loop, daemon=True).start()

    def _webcam_loop(self):
        """Tourne dans un thread dedie : lit la webcam partagee en continu et
        stocke la derniere image PIL dans self._webcam_frame. La conversion
        en PhotoImage Tk (non thread-safe) est faite par _draw() dans le
        thread UI."""
        from tools import webcam as webcam_mod
        try:
            import cv2
            from PIL import Image
        except Exception:
            self._webcam_active.clear()
            return
        cap = webcam_mod.acquire()
        if cap is None:
            self._webcam_active.clear()
            return
        try:
            while self._webcam_active.is_set() and self._running:
                frame = webcam_mod.read_locked()
                if frame is None:
                    time.sleep(0.05)
                    continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb).transpose(Image.FLIP_LEFT_RIGHT)
                img.thumbnail((220, 165))
                self._webcam_frame = img
                time.sleep(0.04)
        finally:
            webcam_mod.release()

    # ── Champ de saisie texte (Ctrl+T) ───────────────────────────────────────

    def _toggle_text_entry(self):
        if self._text_entry_visible:
            self._hide_text_entry()
        else:
            self._text_entry.place(relx=0.5, rely=0.91, relwidth=0.5, height=34, anchor="center")
            self._text_entry.focus_set()
            self._text_entry_visible = True

    def _hide_text_entry(self, event=None):
        self._text_var.set("")
        self._text_entry.place_forget()
        self._text_entry_visible = False
        self.root.focus_force()
        return "break"

    def _submit_text(self, event=None):
        texte = self._text_var.get().strip()
        if not texte:
            return
        self._text_var.set("")
        self._text_entry.place_forget()
        self._text_entry_visible = False
        self.root.focus_force()

        if self._live_mode:
            if self._live_session and self._live_session.send_text(texte):
                self._user_var.set(f'« {texte} »')
                self._reply_var.set("")
            else:
                self._set_state("ERREUR", "", "Mode Live : session non prete pour le texte.")
        else:
            threading.Thread(target=self._process_user_text, args=(texte,), daemon=True).start()

    # ── Contrôles ─────────────────────────────────────────────────────────────

    def _toggle_fs(self):
        fs = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not fs)

    def _on_escape(self):
        """Échap : arrête d'abord une lecture à voix haute, sinon quitte."""
        if _reading_aloud():
            threading.Thread(target=sys.modules["tools.reader"].stop_reading, daemon=True).start()
            return
        self._quit()

    def _quit(self):
        self._running = False
        if _reading_aloud():
            sys.modules["tools.reader"].stop_reading()
        self._webcam_active.clear()
        if self._live_session:
            self._live_session.stop()
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    AmahVoiceUI().run()