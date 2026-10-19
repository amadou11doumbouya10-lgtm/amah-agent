"""
Amah Listener — Détection du mot de réveil
Tourne en arrière-plan, écoute le micro en permanence.
Quand tu dis "Amah", l'interface vocale plein écran s'ouvre.

Lancement : py -3.13 amah_listener.py
Quitter   : clic droit sur le widget → Quitter
Backup    : Ctrl+Shift+A ouvre l'interface directement
"""
import os
import sys
import math
import time
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from dotenv import load_dotenv

_env = (Path(sys.executable).parent / ".env"
        if getattr(sys, "frozen", False)
        else Path(__file__).parent / ".env")
load_dotenv(_env)

# ── Mot de réveil hors ligne (Vosk) ─────────────────────────────────────────
# Google transcrit mal "Amah" dit seul (prénom court et rare) : avec la vraie
# voix de l'utilisateur, presque toujours "rien compris" (test du 18/10/2026).
# Vosk tourne sur le PC avec une liste de mots restreinte : il ne cherche que
# "ama" — mot connu de son vocabulaire, prononcé comme "Amah" — au milieu de
# mots concurrents qui lui ressemblent ("arrête", "fais-moi", "ami"…), sinon
# "arrête la lecture" ou "fais-moi le point" réveillaient Amah. Mesuré : 6/6
# réveils (voix de synthèse), 4/4 sur les vrais enregistrements de
# l'utilisateur que Google ne comprenait pas, 0/48 faux réveils.
# Sans Vosk ou sans modèle : repli automatique sur Google.
VOSK_MODEL = (Path(sys.executable).parent if getattr(sys, "frozen", False)
              else Path(__file__).parent) / "models" / "vosk-model-small-fr-0.22"
WAKE_GRAMMAR = [
    "ama",
    # Concurrents : sons proches de "ama" qui doivent gagner à sa place
    "arrête", "arrêter", "fais", "fait", "moi", "ami", "amis", "amie", "allô", "alors",
    "allez", "mais", "madame", "maman", "la", "le", "les", "point", "à", "au", "avec",
    "aussi", "merci", "comment", "quelle", "qui", "quoi", "tu", "je", "est", "il",
    "elle", "oui", "non", "salut", "bonjour",
    "[unk]",
]
WAKE_MIN_CONFIDENCE = 0.85


def vosk_wake(result: dict):
    """Résultat Vosk -> (réveil ?, confiance de "ama" ou None). Le nom doit être
    le PREMIER mot (on appelle Amah avant de parler) : "au revoir Amah" ne
    réveille pas."""
    words = result.get("result") or []
    if not words or words[0].get("word") != "ama":
        return False, None
    conf = float(words[0].get("conf", 0))
    return conf >= WAKE_MIN_CONFIDENCE, conf


def _already_running() -> bool:
    """Vérifie si une autre instance de amah_listener.py tourne déjà.

    Sans ce garde-fou, un second lancement (ex: double clic sur le bouton
    "Amah écoute") fait écouter deux instances en parallèle : si les deux
    détectent le mot de réveil, on obtient deux interfaces vocales
    superposées (voix dédoublée, réponses incohérentes)."""
    try:
        import psutil
    except ImportError:
        return False
    me = os.getpid()
    script_name = Path(__file__).name
    for proc in psutil.process_iter(["pid", "cmdline"]):
        if proc.info["pid"] == me:
            continue
        try:
            cmdline = proc.info["cmdline"] or []
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if any(script_name in str(arg) for arg in cmdline):
            return True
    return False

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#03050a"
CYAN     = "#00d4ff"
CYAN_DIM = "#003845"
GREEN    = "#00ff88"
RED      = "#ff3355"
GOLD     = "#c8a96e"

# Variantes phonétiques de "Amah" que Google peut transcrire
WAKE_WORDS = {
    "amah", "ama", "amas", "amax",
    "emma", "ema", "amor",
    "mah", "amah.",
    "hamah", "ah mah",
    # Transcription Google la plus fréquente de "Amah" (banc vocal du
    # 18/10/2026 : 6 fois sur 8 avec les voix Henri et Denise)
    "hama", "hamma", "amma",
    # Voix réelle de l'utilisateur (test du 18/10/2026)
    "ahma",
}


# ── Widget de fond (coin bas-droit) ───────────────────────────────────────────

class ListenerWidget:

    SIZE = 80

    def __init__(self):
        self._frame      = 0
        self._running    = True
        self._state      = "INIT"
        self._color      = CYAN_DIM
        self._voice_open = False
        self._last_text  = ""          # dernier texte reconnu (debug)
        self._drag_x     = 0
        self._drag_y     = 0
        self._dragged    = False

        self._build()
        self._animate()
        threading.Thread(target=self._listen_loop, daemon=True).start()
        self._start_hotkey()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build(self):
        self.root = tk.Tk()
        self.root.title("Amah Listener")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.90)
        self.root.configure(bg=BG)
        # Lancee par gui.py (processus en arriere-plan), la fenetre est creee
        # sans le style WS_VISIBLE (Windows ne l'affiche jamais, meme avec
        # "-topmost") : deiconify() force son affichage ; lift()/focus_force()
        # la passent ensuite au premier plan.
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.SIZE}x{self.SIZE}+{sw - self.SIZE - 16}+{sh - self.SIZE - 52}")

        self.canvas = tk.Canvas(self.root, width=self.SIZE, height=self.SIZE,
                                bg=BG, highlightthickness=0)
        self.canvas.pack()

        self._menu = tk.Menu(self.root, tearoff=0,
                             bg="#0a1020", fg=CYAN, font=("Consolas", 9),
                             activebackground=CYAN_DIM, activeforeground=CYAN)
        self._menu.add_command(label="Ouvrir interface vocale", command=self._open_voice)
        self._menu.add_command(label="Masquer le widget (Ctrl+Shift+M pour le revoir)",
                               command=self._hide)
        self._menu.add_separator()
        self._menu.add_command(label="Quitter Amah Listener", command=self._quit)

        self.canvas.bind("<Button-3>",        self._show_menu)
        self.canvas.bind("<ButtonPress-1>",   self._drag_start)
        self.canvas.bind("<B1-Motion>",       self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _drag_start(self, e):
        self._drag_x  = e.x
        self._drag_y  = e.y
        self._dragged = False

    def _drag_move(self, e):
        dx, dy = e.x - self._drag_x, e.y - self._drag_y
        if abs(dx) > 3 or abs(dy) > 3:
            self._dragged = True
            self.root.geometry(f"+{self.root.winfo_x() + dx}+{self.root.winfo_y() + dy}")

    def _on_release(self, _):
        if not self._dragged:
            self._open_voice()

    def _show_menu(self, e):
        self._menu.tk_popup(e.x_root, e.y_root)

    # ── Animation ─────────────────────────────────────────────────────────────

    def _animate(self):
        if not self._running:
            return
        self._frame += 1
        self._draw()
        self.root.after(50, self._animate)

    def _draw(self):
        c  = self.canvas
        f  = self._frame
        s  = self.SIZE
        cx = cy = s // 2
        col = self._color
        c.delete("all")

        # Echelle par rapport a la taille de reference (120px) -- permet de
        # reduire SIZE sans que le dessin (halos, hexagone, textes...) soit
        # rogne ou desproportionne.
        k = s / 120.0

        # Fond
        c.create_rectangle(0, 0, s, s, fill=BG, outline=col, width=1)

        # Halos
        for r, a in [(46, 0.07), (34, 0.13), (22, 0.20)]:
            r *= k
            c.create_oval(cx-r, cy-r-4*k, cx+r, cy+r-4*k,
                          fill=_blend(BG, col, a), outline="")

        # Hexagone rotatif
        pts = _hex_pts(cx, cy - 6*k, (26 + 2 * math.sin(math.radians(f * 4))) * k,
                       offset=f * 1.4)
        c.create_polygon(pts, outline=col, fill="", width=1)

        # Orbe "A"
        orb = (15 + 1.5 * math.sin(math.radians(f * 7))) * k
        c.create_oval(cx-orb, cy-6*k-orb, cx+orb, cy-6*k+orb,
                      fill=_blend(BG, col, 0.18), outline=col, width=1)
        c.create_text(cx, cy - 6*k, text="A", fill=col,
                      font=("Consolas", max(7, round(13 * k)), "bold"))

        # État
        label = {"INIT":"...", "CALIB":"CALIB",
                 "ECOUTE":"ECOUTE", "DETECTION":"AMAH !",
                 "ACTIVE":"ACTIVE", "ERREUR":"ERREUR"}.get(self._state, self._state)
        c.create_text(cx, cy + 22*k, text=label, fill=col,
                      font=("Consolas", max(6, round(8 * k)), "bold"))

        # Dernier texte reconnu (debug, max 14 chars)
        if self._last_text:
            preview = self._last_text[:14]
            c.create_text(cx, cy + 34*k, text=preview, fill=_blend(BG, col, 0.6),
                          font=("Consolas", max(5, round(6 * k))))

        # Barre pulsante
        bw = (12 + 20 * abs(math.sin(math.radians(f * 6)))) * k
        c.create_rectangle(cx - bw, cy + 42*k, cx + bw, cy + 45*k,
                           fill=col, outline="")

        # Coins HUD
        L, P = 8*k, 4*k
        for ax, ay, dx, dy in [(P,P,1,1),(s-P,P,-1,1),(P,s-P,1,-1),(s-P,s-P,-1,-1)]:
            c.create_line(ax, ay, ax+dx*L, ay, fill=col, width=1)
            c.create_line(ax, ay, ax, ay+dy*L, fill=col, width=1)

    # ── Boucle de reconnaissance ──────────────────────────────────────────────

    def _listen_loop(self):
        """Écoute du mot de réveil : Vosk hors ligne, sinon Google."""
        try:
            import pyaudio
            from vosk import KaldiRecognizer, Model, SetLogLevel
            if not VOSK_MODEL.exists():
                raise FileNotFoundError(f"modèle Vosk absent : {VOSK_MODEL}")
        except Exception as e:
            self._last_text = f"repli Google ({type(e).__name__})"
            return self._listen_loop_google()
        try:
            from tools import journal          # journal de session (AMAH_JOURNAL=1)
        except Exception:
            journal = None

        import json
        SetLogLevel(-1)
        try:
            self._set("CALIB", CYAN_DIM)
            model = Model(str(VOSK_MODEL))
            rate = 16000
            rec = KaldiRecognizer(model, rate, json.dumps(WAKE_GRAMMAR, ensure_ascii=False))
            rec.SetWords(True)
            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=rate,
                             input=True, frames_per_buffer=4000)
        except Exception as e:
            self._last_text = f"micro : {str(e)[:30]}"
            self._set("ERREUR", RED)
            try:
                from tools.conversation import log_error
                log_error("mot de réveil | Vosk / micro", e)
            except Exception:
                pass
            return

        self._set("ECOUTE", CYAN_DIM)
        was_open = False
        try:
            while self._running:
                data = stream.read(4000, exception_on_overflow=False)   # 0,25 s
                if self._voice_open:
                    was_open = True        # l'interface vocale écoute à sa place
                    continue
                if was_open:
                    was_open = False
                    rec.Reset()
                if not rec.AcceptWaveform(data):
                    continue
                result = json.loads(rec.Result())
                woke, conf = vosk_wake(result)
                if conf is None:
                    continue               # pas de "ama" en tête : rien à noter
                heard = f"ama (confiance {conf:.2f}, hors ligne)".replace(".", ",", 1)
                self._last_text = "ama"
                if journal:
                    journal.wake(heard, woke)
                if woke:
                    self._set("DETECTION", CYAN)
                    self.root.after(0, self._open_voice)
                    time.sleep(2)
                    rec.Reset()
                else:
                    self._set("ECOUTE", CYAN_DIM)
        finally:
            try:
                stream.close()
                pa.terminate()
            except Exception:
                pass

    def _listen_loop_google(self):
        """Repli sans Vosk : reconnaissance Google de chaque phrase entendue."""
        try:
            import speech_recognition as sr
        except ImportError:
            self._set("ERREUR", RED)
            return
        try:
            from tools import journal          # journal de session (AMAH_JOURNAL=1)
        except Exception:
            journal = None

        r   = sr.Recognizer()
        r.energy_threshold         = 150
        r.dynamic_energy_threshold = False  # seuil fixe — evite que le bruit ambiant monte le seuil trop haut
        # Test avec la vraie voix (18/10/2026) :
        # - pause_threshold 0,25 (v1.5.1) < non_speaking_duration 0,5 par défaut :
        #   AssertionError au calibrage, le fil d'écoute s'arrêtait sans message
        #   et le widget n'écoutait plus rien depuis la v1.5.1 (06/08/2026) ;
        # - 0,25 s de pause hachait aussi "Amah" en fragments que Google ne
        #   comprenait pas : 0,5 s (valeur d'origine), 0,4 s gardée avant la voix.
        r.pause_threshold          = 0.5
        # Reconnaissance Google : 6 s maximum (sans limite, une réponse réseau
        # perdue figeait l'écoute pour toujours — vu le 18/10/2026)
        r.operation_timeout        = 6
        r.non_speaking_duration    = 0.4

        try:
            mic = sr.Microphone()
            self._set("CALIB", CYAN_DIM)
            with mic as src:
                r.adjust_for_ambient_noise(src, duration=0.5)
            # Seuil proche de celui de l'interface vocale (le niveau de la pièce,
            # ~80), qui entend bien l'utilisateur. Un plancher à 300 ratait sa
            # voix à distance normale du micro (aucun appel capté pendant 7 min,
            # test du 18/10/2026) ; les petits bruits ne hachent plus la voix
            # depuis que la pause est à 0,5 s, au pire un "rien compris".
            r.energy_threshold = max(r.energy_threshold * 1.2, 120)
        except Exception as e:
            # Micro absent, occupé ou refusé : le dire au lieu d'un widget muet
            self._last_text = f"micro : {str(e)[:30]}"
            self._set("ERREUR", RED)
            try:
                from tools.conversation import log_error
                log_error("mot de réveil | ouverture du micro", e)
            except Exception:
                pass
            return

        self._set("ECOUTE", CYAN_DIM)

        while self._running:
            if self._voice_open:
                time.sleep(0.8)
                continue

            try:
                with mic as src:
                    audio = r.listen(src, timeout=4, phrase_time_limit=3)

                text = ""
                try:
                    text = r.recognize_google(audio, language="fr-FR").lower().strip()
                except sr.UnknownValueError:
                    if journal:
                        journal.wake("", False)

                if text:
                    self._last_text = text
                    woke = self._is_wake(text)
                    if journal:
                        journal.wake(text, woke)
                    if woke:
                        self._set("DETECTION", CYAN)
                        self.root.after(0, self._open_voice)
                        time.sleep(2)
                    else:
                        self._set("ECOUTE", CYAN_DIM)

            except sr.WaitTimeoutError:
                pass
            except sr.RequestError as e:
                self._last_text = f"réseau: {str(e)[:20]}"
                self._set("ERREUR", RED)
                time.sleep(2)
                self._set("ECOUTE", CYAN_DIM)
            except Exception as e:
                self._last_text = str(e)[:20]
                time.sleep(0.5)

    @staticmethod
    def _edit_distance(a: str, b: str) -> int:
        """Distance de Levenshtein simple (pour tolérer les fautes de transcription)."""
        if a == b:
            return 0
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            curr = [i] + [0] * len(b)
            for j, cb in enumerate(b, 1):
                curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb))
            prev = curr
        return prev[-1]

    def _is_wake(self, text: str) -> bool:
        """Vérifie si le texte contient une variante du mot de réveil "Amah"."""
        words = text.lower().split()
        # "Amah" dit rapidement (~0,4 s) est transcrit "am" (voix réelle, test du
        # 18/10/2026 : 2 fois sur 4) ; accepté en premier mot seulement, pas au
        # milieu d'une phrase, pour éviter les faux réveils
        if words and words[0].strip(".,!?") == "am":
            return True
        for w in words:
            w = w.strip(".,!?")
            if not w:
                continue
            if w in WAKE_WORDS:
                return True
            # Tolère les transcriptions proches ("amat", "amaa"…) sans matcher
            # des mots français courants comme "ami", "amour", "amène".
            if 3 <= len(w) <= 6 and self._edit_distance(w, "amah") <= 1:
                return True
        return False

    # ── Raccourci clavier global ──────────────────────────────────────────────

    def _start_hotkey(self):
        """Ctrl+Shift+A → ouvre l'interface vocale, Ctrl+Shift+M → affiche/masque
        le widget (backup clavier, utile si la reconnaissance vocale échoue ou
        si le widget est masqué)."""
        try:
            from pynput import keyboard as kb

            h = kb.GlobalHotKeys({
                "<ctrl>+<shift>+a": lambda: self.root.after(0, self._open_voice),
                "<ctrl>+<shift>+m": lambda: self.root.after(0, self._toggle_visibility),
            })
            t = threading.Thread(target=h.run, daemon=True)
            t.start()
        except Exception:
            pass   # pynput non installé — pas grave, la voix reste

    # ── Helpers état ─────────────────────────────────────────────────────────

    def _set(self, state: str, color: str):
        self._state = state
        self._color = color

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_voice(self):
        if self._voice_open:
            return
        self._voice_open = True
        self._set("ACTIVE", GREEN)

        script = str(Path(__file__).parent / "voice_fullscreen.py")
        flags  = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        def _run():
            proc = subprocess.Popen([sys.executable, script], creationflags=flags)
            proc.wait()
            self._voice_open = False
            self._last_text  = ""
            self._set("ECOUTE", CYAN_DIM)

        threading.Thread(target=_run, daemon=True).start()

    def _hide(self):
        """Cache le widget de l'écran sans rien arrêter : la détection du mot
        de réveil tourne dans son propre thread et continue d'écouter même
        fenêtre masquée. Ctrl+Shift+M (ou redire "Amah") le fait revenir."""
        self.root.withdraw()

    def _toggle_visibility(self):
        if self.root.state() == "withdrawn":
            self.root.deiconify()
        else:
            self.root.withdraw()

    def _quit(self):
        self._running = False
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t))

def _hex_pts(cx, cy, r, offset=0):
    pts = []
    for i in range(6):
        a = math.radians(60 * i + offset)
        pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return pts


# ── Point d'entrée ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if _already_running():
        from tkinter import messagebox
        _root = tk.Tk()
        _root.withdraw()
        messagebox.showinfo("Amah",
            "Amah écoute déjà en arrière-plan\n(widget en bas à droite de l'écran).")
        _root.destroy()
        sys.exit(0)
    ListenerWidget().run()
