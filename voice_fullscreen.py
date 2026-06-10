"""
Amah Agent — Interface Vocale Plein Écran
Style : HUD futuriste / cyberpunk (hexagone central, grille, coins HUD)
Lancement : py -3.13 voice_fullscreen.py
Quitter   : dire "ferme" / "quitte" / "au revoir"  ou  Échap
"""
import os, sys, json, math, time, threading
from pathlib import Path
from datetime import datetime
import tkinter as tk
from dotenv import load_dotenv

# ── Chargement .env ──────────────────────────────────────────────────────────
_env = (Path(sys.executable).parent / ".env"
        if getattr(sys, "frozen", False)
        else Path(__file__).parent / ".env")
load_dotenv(_env)
from tools.voice import speak
from tools import TOOL_FUNCTIONS
from config import SYSTEM_PROMPT, TOOLS_DEFINITIONS
from groq_client import GroqClient

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

STATES = {
    "IDLE":   (CYAN_DIM,  "AMAH  ·  EN ATTENTE"),
    "ECOUTE": (CYAN,      "ECOUTE..."),
    "PENSE":  (GOLD,      "TRAITEMENT  ·  IA"),
    "REPOND": (GREEN,     "REPOND"),
    "ERREUR": (RED,       "ERREUR"),
}

STOP_WORDS = {
    "ferme","quitte","quitter","stop","au revoir","aurevoir",
    "goodbye","bye","exit","close","arrete","arrête",
}

MODEL_FAST  = "llama-3.1-8b-instant"     # questions simples sans outils (~300ms)
MODEL_FULL  = "llama-3.3-70b-versatile"  # requêtes avec outils (~1-2s)

# ── Routeur d'outils (même logique que gui.py) ───────────────────────────────

_DEFAULT_TOOLS = {
    "web_search","read_webpage","list_files","read_file",
    "open_file","run_command","get_system_info","speak",
    "get_weather_simple","translate","get_datetime","calculate",
}

_WORD_TO_CAT = {
    "liste":"fichiers","lister":"fichiers","fichier":"fichiers","fichiers":"fichiers",
    "dossier":"fichiers","trouve":"fichiers","trouver":"fichiers","deplace":"fichiers",
    "organise":"fichiers","classe":"fichiers","lis":"fichiers","lire":"fichiers",
    "affiche":"fichiers","montre":"fichiers","modifie":"fichiers","modifier":"fichiers",
    "ecris":"fichiers","ecrire":"fichiers","remplace":"fichiers","corrige":"fichiers",
    "html":"fichiers","css":"fichiers","js":"fichiers","py":"fichiers","json":"fichiers",
    "word":"documents","pdf":"documents","txt":"documents","document":"documents",
    "rapport":"documents","cree":"documents","creer":"documents","genere":"documents",
    "redige":"documents","lettre":"documents","facture":"documents","contrat":"documents",
    "web":"internet","recherche":"internet","site":"internet","cherche":"internet",
    "url":"internet","clique":"internet","screenshot":"internet","page":"internet",
    "youtube":"youtube","video":"youtube","musique":"youtube","chanson":"youtube",
    "email":"email","mail":"email","envoie":"email","lis-mes":"email","gmail":"email",
    "memorise":"memoire","souviens":"memoire","rappelle":"memoire","oublie":"memoire",
    "systeme":"systeme","processus":"systeme","reseau":"systeme","ip":"systeme",
    "commande":"systeme","ram":"systeme","cpu":"systeme","disque":"systeme","pc":"systeme",
    "calcule":"utils","convertis":"utils","date":"utils","heure":"utils","zip":"utils",
    "excel":"data","tableau":"data","clipboard":"data","presse-papiers":"data",
    "parle":"media","dis":"media","voix":"media","notification":"media","rappel":"media",
    "image":"images","photo":"images","redimensionne":"images","png":"images","jpg":"images",
    "meteo":"info","temps":"info","traduis":"info","traduction":"info","langue":"info",
    "volume":"hardware","son":"hardware","muet":"hardware","luminosite":"hardware",
    "wifi":"hardware","lumiere":"hardware","sombre":"hardware",
    "vois":"vision","observe":"vision","ecran":"vision","analyse":"vision",
    "mon-ecran":"vision","sur-ecran":"vision","l-ecran":"vision","regarde":"vision",
    "lire-ecran":"vision","lis-ecran":"vision","que-vois":"vision","ecrat":"vision",
    "carte":"internet","cartes":"internet","drapeau":"internet","drapeaux":"internet",
    "vol":"flights","vols":"flights","avion":"flights","billet":"flights","voyage":"flights",
    "plan":"planner","etapes":"planner","sequence":"planner",
    "steam":"jeux","epic":"jeux","jeu":"jeux","jeux":"jeux",
}

_CAT_TOOLS = {
    "fichiers":  {"list_files","organize_folder","find_files","move_file","create_folder","read_file","write_file","edit_file","edit_pdf","get_folder_info"},
    "documents": {"create_word","create_txt","create_pdf","read_document","write_file","edit_file","edit_pdf"},
    "internet":  {"web_search","read_webpage","open_browser","click_element","fill_form","take_screenshot","get_page_text"},
    "email":     {"read_emails","send_email","search_emails"},
    "memoire":   {"save_memory","get_memories","delete_memory"},
    "systeme":   {"get_system_info","open_file","run_command","list_processes","get_network_info"},
    "utils":     {"calculate","get_datetime","add_days","generate_password","convert_units","zip_files","unzip_file","list_archive"},
    "data":      {"read_excel","create_excel","append_to_excel","read_clipboard","write_clipboard"},
    "media":     {"speak","listen","send_notification","set_reminder","screenshot_full"},
    "images":    {"screenshot_full","resize_image","get_image_info","convert_image"},
    "info":      {"get_weather","get_weather_simple","translate","detect_language","get_stats","check_update"},
    "hardware":  {"set_volume","get_audio_level","mute_audio","set_brightness","get_brightness","wifi_toggle"},
    "vision":    {"analyze_screen","screenshot_full"},
    "youtube":   {"open_youtube","search_youtube","open_browser","web_search"},
    "flights":   {"search_flights","web_search","open_browser"},
    "planner":   {"create_plan"},
    "jeux":      {"open_steam","open_epic_games","list_installed_steam_games",
                   "launch_game_steam","search_game_on_steam","install_game_steam"},
}

def _select_tools(message: str):
    words = message.lower().replace("'", " ").split()
    cats  = {_WORD_TO_CAT[w] for w in words if w in _WORD_TO_CAT}
    if not cats:
        needed = _DEFAULT_TOOLS
    else:
        needed = set()
        for cat in cats:
            needed |= _CAT_TOOLS.get(cat, set())
    return [t for t in TOOLS_DEFINITIONS if t["function"]["name"] in needed]


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

        self._build()
        self._grid_img = self._make_grid(self._W, self._H)  # grille pré-rendue 1×
        self._animate()
        threading.Thread(target=self._init_mic, daemon=True).start()
        self.root.after(1800, self._start_loop)

    # ── Construction ─────────────────────────────────────────────────────────

    def _build(self):
        self.root = tk.Tk()
        self.root.title("Amah — Interface Vocale")
        self.root.configure(bg=BG)
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda e: self._quit())
        self.root.bind("<F11>",    lambda e: self._toggle_fs())

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
                 text='Dire  "ferme"  ou  Échap  pour quitter   ·   F11 plein écran',
                 bg=BG, fg=DIM, font=("Consolas", 9),
                 ).place(relx=0.5, rely=0.97, anchor="center")

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
        if self.state in ("ECOUTE", "REPOND"):
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
        c.create_text(40, 28, text="AMAH  AGENT  v1.4",
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

    def _set_state(self, state, user="", reply=""):
        self.state  = state
        self._color = STATES[state][0]
        self._label = STATES[state][1]
        self._user_var.set(user)
        self._reply_var.set(reply)

    def _init_mic(self):
        """Crée Recognizer + Microphone une seule fois et calibre."""
        try:
            import speech_recognition as sr
            self._sr = sr.Recognizer()
            self._sr.pause_threshold        = 0.7   # coupe après 0.7s de silence
            self._sr.energy_threshold       = 300
            self._sr.dynamic_energy_threshold = True
            self._mic = sr.Microphone()
            with self._mic as src:
                self._sr.adjust_for_ambient_noise(src, duration=1.0)
            self._mic_ready = True
        except Exception as e:
            self._mic_ready = False
            self._mic_error = str(e)

    def _listen_once(self):
        """Écoute une phrase (max 6s). Retourne le texte ou None."""
        if not self._mic_ready or self._sr is None:
            time.sleep(0.5)
            return None
        import speech_recognition as sr
        try:
            with self._mic as src:
                audio = self._sr.listen(src, timeout=5, phrase_time_limit=6)
        except sr.WaitTimeoutError:
            return None   # rien dit dans le délai imparti
        try:
            return self._sr.recognize_google(audio, language="fr-FR")
        except sr.UnknownValueError:
            return None   # parole incomprise
        except sr.RequestError as e:
            # Vrai problème (pas de réseau, API Google indisponible…) : à signaler
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
        while self._running:
            texte = self._listen_once()
            if not texte:
                continue

            texte = texte.strip()

            # Fermeture vocale
            if any(w in texte.lower() for w in STOP_WORDS):
                self.root.after(0, self._set_state, "IDLE", texte, "À bientôt.")
                speak("À bientôt.")
                time.sleep(0.3)
                self.root.after(0, self._quit)
                return

            # Traitement
            self.root.after(0, self._set_state, "PENSE", f'« {texte} »', "")
            reply, is_err = self._chat(texte)

            short = reply if len(reply) <= 220 else reply[:217] + "…"
            if is_err:
                self.root.after(0, self._set_state, "ERREUR", f'« {texte} »', short)
                time.sleep(2.5)
            else:
                self.root.after(0, self._set_state, "REPOND", f'« {texte} »', short)
                # speak() est bloquant : on attend la fin réelle de la voix
                # au lieu d'estimer une durée, et on affiche l'erreur si la
                # synthèse échoue plutôt que de l'avaler en silence.
                voice_res = speak(reply[:450], speed=2)
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

        tools = _select_tools(text)
        model = MODEL_FULL if tools else MODEL_FAST

        def _on_status(txt):
            # Affiche les messages de rotation/attente (limite Groq) dans la
            # zone de reponse au lieu de laisser l'ecran fige sur "TRAITEMENT".
            self.root.after(0, self._reply_var.set, txt)

        def _call(msgs, tl):
            return self.client.chat(
                messages=msgs, model=model, tools=tl,
                max_tokens=1024, temperature=0.4,
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
                    tools = TOOLS_DEFINITIONS
                    return _call(msgs, tools)
                raise

        try:
            resp = _call_safe(self.messages)
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
                    res = self._run_tool(tc)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": res,
                    })
                resp = _call_safe(self.messages)

            reply = resp.choices[0].message.content or "Compris."
            self.messages.append({"role": "assistant", "content": reply})
            return reply, False
        except Exception as e:
            return f"Erreur API : {e}", True

    def _run_tool(self, tc) -> str:
        try:
            args = json.loads(tc.function.arguments) or {}
        except Exception:
            args = {}
        func = TOOL_FUNCTIONS.get(tc.function.name)
        if not func:
            return json.dumps({"error": f"Outil inconnu: {tc.function.name}"})
        try:
            return json.dumps(func(**args), ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ── Contrôles ─────────────────────────────────────────────────────────────

    def _toggle_fs(self):
        fs = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not fs)

    def _quit(self):
        self._running = False
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    AmahVoiceUI().run()
