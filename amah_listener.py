"""
Amah Listener — Détection du mot de réveil
Tourne en arrière-plan, écoute le micro en permanence.
Quand tu dis "Amah", l'interface vocale plein écran s'ouvre.

Lancement : py -3.13 amah_listener.py
Quitter   : clic droit sur le widget → Quitter
Backup    : Ctrl+Shift+A ouvre l'interface directement
"""
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
}


# ── Widget de fond (coin bas-droit) ───────────────────────────────────────────

class ListenerWidget:

    SIZE = 120

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

        # Fond
        c.create_rectangle(0, 0, s, s, fill=BG, outline=col, width=1)

        # Halos
        for r, a in [(46, 0.07), (34, 0.13), (22, 0.20)]:
            c.create_oval(cx-r, cy-r-4, cx+r, cy+r-4,
                          fill=_blend(BG, col, a), outline="")

        # Hexagone rotatif
        pts = _hex_pts(cx, cy - 6, 26 + 2 * math.sin(math.radians(f * 4)),
                       offset=f * 1.4)
        c.create_polygon(pts, outline=col, fill="", width=1)

        # Orbe "A"
        orb = 15 + 1.5 * math.sin(math.radians(f * 7))
        c.create_oval(cx-orb, cy-6-orb, cx+orb, cy-6+orb,
                      fill=_blend(BG, col, 0.18), outline=col, width=1)
        c.create_text(cx, cy - 6, text="A", fill=col,
                      font=("Consolas", 13, "bold"))

        # État
        label = {"INIT":"...", "CALIB":"CALIB",
                 "ECOUTE":"ECOUTE", "DETECTION":"AMAH !",
                 "ACTIVE":"ACTIVE", "ERREUR":"ERREUR"}.get(self._state, self._state)
        c.create_text(cx, cy + 22, text=label, fill=col,
                      font=("Consolas", 8, "bold"))

        # Dernier texte reconnu (debug, max 12 chars)
        if self._last_text:
            preview = self._last_text[:14]
            c.create_text(cx, cy + 34, text=preview, fill=_blend(BG, col, 0.6),
                          font=("Consolas", 6))

        # Barre pulsante
        bw = int(12 + 20 * abs(math.sin(math.radians(f * 6))))
        c.create_rectangle(cx - bw, cy + 42, cx + bw, cy + 45,
                           fill=col, outline="")

        # Coins HUD
        L, P = 8, 4
        for ax, ay, dx, dy in [(P,P,1,1),(s-P,P,-1,1),(P,s-P,1,-1),(s-P,s-P,-1,-1)]:
            c.create_line(ax, ay, ax+dx*L, ay, fill=col, width=1)
            c.create_line(ax, ay, ax, ay+dy*L, fill=col, width=1)

    # ── Boucle de reconnaissance ──────────────────────────────────────────────

    def _listen_loop(self):
        try:
            import speech_recognition as sr
        except ImportError:
            self._set("ERREUR", RED)
            return

        r   = sr.Recognizer()
        r.energy_threshold       = 250
        r.dynamic_energy_threshold = True
        r.pause_threshold        = 0.5

        try:
            mic = sr.Microphone()
        except Exception:
            self._set("ERREUR", RED)
            return

        self._set("CALIB", CYAN_DIM)
        with mic as src:
            r.adjust_for_ambient_noise(src, duration=1.2)

        self._set("ECOUTE", CYAN_DIM)

        while self._running:
            if self._voice_open:
                time.sleep(0.8)
                continue

            try:
                with mic as src:
                    audio = r.listen(src, timeout=4, phrase_time_limit=3)

                # Essai français d'abord, puis anglais en fallback
                text = ""
                for lang in ("fr-FR", "en-US"):
                    try:
                        text = r.recognize_google(audio, language=lang).lower().strip()
                        break
                    except sr.UnknownValueError:
                        continue

                if text:
                    self._last_text = text
                    if self._is_wake(text):
                        self._set("DETECTION", CYAN)
                        self.root.after(0, self._open_voice)
                        time.sleep(2)
                    else:
                        self._set("ECOUTE", CYAN_DIM)

            except sr.WaitTimeoutError:
                pass
            except Exception:
                time.sleep(0.5)

    def _is_wake(self, text: str) -> bool:
        """Vérifie si le texte contient une variante du mot de réveil."""
        words = text.split()
        for w in words:
            w = w.strip(".,!?")
            if w in WAKE_WORDS:
                return True
            # Distance phonétique simple : commence par "am" ou "em" + courte
            if len(w) <= 5 and (w.startswith("am") or w.startswith("em")):
                return True
        return False

    # ── Raccourci clavier global ──────────────────────────────────────────────

    def _start_hotkey(self):
        """Ctrl+Shift+A → ouvre l'interface vocale (backup si reconnaissance échoue)."""
        try:
            from pynput import keyboard as kb

            def _on_activate():
                self.root.after(0, self._open_voice)

            h = kb.GlobalHotKeys({"<ctrl>+<shift>+a": _on_activate})
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
    ListenerWidget().run()
