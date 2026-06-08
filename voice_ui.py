"""Interface vocale animée d'Amah — style HUD inspiré de Mark XXXIX."""
import tkinter as tk
import threading
import math

# ── Palette ─────────────────────────────────────────────────────────────────
BG       = "#080806"
GOLD     = "#c8a96e"
GOLD_DIM = "#5a4020"
GOLD_LT  = "#e0c88e"
CYAN     = "#4ecdc4"
GREEN    = "#27ae60"
RED      = "#c0392b"
WHITE    = "#e8e0d0"
DIM      = "#3a3a32"

W, H     = 420, 500   # taille de la fenêtre
CX, CY   = W // 2, 175  # centre de l'animation

# ── Couleurs par état ────────────────────────────────────────────────────────
_STATE_COLORS = {
    "ECOUTE":      GOLD,
    "TRAITEMENT":  CYAN,
    "OK":          GREEN,
    "ERREUR":      RED,
    "IDLE":        GOLD_DIM,
}
_STATE_LABELS = {
    "ECOUTE":      "ECOUTE...",
    "TRAITEMENT":  "TRAITEMENT",
    "OK":          "OK",
    "ERREUR":      "ERREUR",
    "IDLE":        "AMAH",
}


def _hex_blend(c1: str, c2: str, t: float) -> str:
    """Interpole linéairement entre deux couleurs hexadécimales."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


class VoiceWindow:
    """Fenêtre HUD animée pour l'entrée vocale.

    Paramètres
    ----------
    parent    : fenêtre tkinter parente
    on_result : callback(text: str) appelé si la transcription réussit
    """

    def __init__(self, parent: tk.Tk, on_result):
        self.parent    = parent
        self.on_result = on_result
        self.state     = "IDLE"
        self._frame    = 0
        self._alive    = True

        self._build_window()
        self._animate()
        self._start_listen()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build_window(self):
        self.win = tk.Toplevel(self.parent)
        self.win.title("Amah — Voix")
        self.win.configure(bg=BG)
        self.win.resizable(False, False)
        self.win.transient(self.parent)
        self.win.grab_set()

        # Centrage sur la fenêtre parente
        self.win.update_idletasks()
        px = self.parent.winfo_x() + (self.parent.winfo_width()  - W) // 2
        py = self.parent.winfo_y() + (self.parent.winfo_height() - H) // 2
        self.win.geometry(f"{W}x{H}+{px}+{py}")

        # Canvas principal (animation HUD)
        self.canvas = tk.Canvas(self.win, width=W, height=H - 100,
                                bg=BG, highlightthickness=0)
        self.canvas.pack()

        # Texte de transcription
        self._txt_var = tk.StringVar(value="")
        tk.Label(self.win, textvariable=self._txt_var,
                 bg=BG, fg=WHITE, font=("Consolas", 11),
                 wraplength=380, justify="center").pack(pady=(4, 2))

        # Bouton annuler
        self._cancel_btn = tk.Button(
            self.win, text="Annuler",
            bg="#1a1a14", fg=DIM,
            font=("Consolas", 10), relief=tk.FLAT, padx=20, pady=5,
            cursor="hand2", activebackground="#2a2a22", activeforeground=GOLD,
            command=self._cancel,
        )
        self._cancel_btn.pack(pady=6)
        self.win.protocol("WM_DELETE_WINDOW", self._cancel)

    # ── Animation ─────────────────────────────────────────────────────────────

    def _animate(self):
        if not self._alive:
            return
        self._frame += 1
        self._draw_frame()
        self.win.after(50, self._animate)   # ~20 fps

    def _draw_frame(self):
        c  = self.canvas
        f  = self._frame
        cx, cy = CX, CY
        c.delete("all")

        color = _STATE_COLORS.get(self.state, GOLD_DIM)
        label = _STATE_LABELS.get(self.state, "AMAH")

        # ── Fond : cercles de gradient ────────────────────────────────────
        for r, alpha in [(150, 0.08), (110, 0.12), (75, 0.18)]:
            fill = _hex_blend(BG, color, alpha)
            c.create_oval(cx-r, cy-r, cx+r, cy+r,
                          fill=fill, outline="")

        # ── Anneau extérieur rotatif (12 points) ─────────────────────────
        r_out = 132
        for i in range(12):
            angle = math.radians(f * 2.2 + i * 30)
            px = cx + r_out * math.cos(angle)
            py = cy + r_out * math.sin(angle)
            bright = 0.2 + 0.8 * (0.5 + 0.5 * math.sin(math.radians(f * 4 + i * 30)))
            col = _hex_blend(GOLD_DIM, color, bright)
            c.create_oval(px - 4, py - 4, px + 4, py + 4, fill=col, outline="")

        # ── Anneau intermédiaire (tirets contra-rotatifs) ─────────────────
        r_mid = 96
        for i in range(8):
            angle = math.radians(-f * 1.8 + i * 45)
            x1 = cx + (r_mid - 10) * math.cos(angle)
            y1 = cy + (r_mid - 10) * math.sin(angle)
            x2 = cx + (r_mid + 10) * math.cos(angle)
            y2 = cy + (r_mid + 10) * math.sin(angle)
            c.create_line(x1, y1, x2, y2, fill=color, width=2)

        # ── Ligne de scan (style radar) ───────────────────────────────────
        scan = math.radians(f * 3.5)
        c.create_line(cx, cy,
                      cx + 125 * math.cos(scan),
                      cy + 125 * math.sin(scan),
                      fill=color, width=1, dash=(5, 8))

        # ── Anneau intérieur (pulsant) ─────────────────────────────────────
        pulse = 62 + 7 * math.sin(math.radians(f * 6))
        c.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse,
                      outline=color, width=2)

        # ── Orbe central ──────────────────────────────────────────────────
        orb_r = 44 + 4 * math.sin(math.radians(f * 8))
        c.create_oval(cx - orb_r, cy - orb_r, cx + orb_r, cy + orb_r,
                      fill=BG, outline=color, width=3)
        c.create_text(cx, cy, text="A", fill=color,
                      font=("Consolas", 30, "bold"))

        # ── Croix centrale (style Amah) ───────────────────────────────────
        arm = 12
        c.create_line(cx - arm, cy, cx + arm, cy, fill=color, width=1)
        c.create_line(cx, cy - arm, cx, cy + arm, fill=color, width=1)

        # ── Label état ────────────────────────────────────────────────────
        c.create_text(cx, cy + 95, text=label, fill=color,
                      font=("Consolas", 12, "bold"))

        # ── Barres audio (actives en mode ECOUTE) ─────────────────────────
        if self.state in ("ECOUTE", "TRAITEMENT"):
            n, sp = 18, 11
            x0 = cx - (n * sp) // 2
            y_mid = cy + 145
            for i in range(n):
                h_bar = 5 + 18 * abs(math.sin(math.radians(f * 9 + i * 22)))
                x = x0 + i * sp
                col = GOLD_LT if i % 2 == 0 else color
                c.create_rectangle(x, y_mid - h_bar, x + 7, y_mid + h_bar,
                                   fill=col, outline="")

    # ── Logique vocale ────────────────────────────────────────────────────────

    def _set_state(self, state: str, text: str = ""):
        self.state = state
        self._txt_var.set(text)

    def _start_listen(self):
        self._set_state("ECOUTE", "Je t'ecoute...")
        threading.Thread(target=self._listen_thread, daemon=True).start()

    def _listen_thread(self):
        try:
            from tools.voice_recognition import listen
            result = listen(timeout=8, language="fr-FR")
        except Exception as e:
            result = {"error": str(e)}

        if not self._alive:
            return

        if result.get("success"):
            self.win.after(0, self._on_success, result["texte"])
        else:
            self.win.after(0, self._on_error, result.get("error", "Erreur inconnue"))

    def _on_success(self, text: str):
        short = text if len(text) <= 80 else text[:77] + "..."
        self._set_state("TRAITEMENT", f'"{short}"')
        self.win.after(1000, self._close_success, text)

    def _close_success(self, text: str):
        if not self._alive:
            return
        self._alive = False
        try:
            self.win.destroy()
        except Exception:
            pass
        self.on_result(text)

    def _on_error(self, error: str):
        short = error[:70]
        self._set_state("ERREUR", short)
        self.win.after(3000, self._cancel)

    def _cancel(self):
        self._alive = False
        try:
            self.win.destroy()
        except Exception:
            pass
