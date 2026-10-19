"""Les mêmes 10 demandes envoyées aux 3 interfaces (gui.py, voice_fullscreen.py,
agent.py), sans fenêtre ni micro — test de référence de l'étape 1 du plan
Amah Core : quand les 3 interfaces passeront par le Core, tout doit être vert.

APPELLE GROQ : ~25 appels, ~150 000 tokens (dont ~80 000 sur gpt-oss-120b) ;
pauses de 15 s pour ne pas saturer les 8 000 tokens/minute par clé.

Lancer depuis la racine du projet :
    py -3.13 -m benchmarks.benchmark_interfaces              # les 3 interfaces
    py -3.13 -m benchmarks.benchmark_interfaces --interface voix
    py -3.13 -m benchmarks.benchmark_interfaces --sans-ia    # 4 demandes, 0 token

Effets réels simulés (suppression, envoi, voix, navigateur…) mais garde-fou
réel : une action sensible doit demander confirmation. La lecture à voix
haute démarre pour de vrai, sans son. Rien n'est écrit dans amah_memory.db.
Mesuré le 18/10/2026 : fenêtre 10/10, voix 10/10, terminal 9/10 ("2 outils" :
le terminal n'enchaîne qu'un outil).
Code de sortie 1 si une vérification échoue.
"""
import builtins, functools, io, json, os, re, subprocess, sys, tempfile, time

SCENARIOS = [
    # (nom, demande, vérification)
    ("instantané", "quelle heure est-il ?", lambda r: r["ia"] == 0 and "Il est" in r["reponse"]),
    ("briefing", "fais-moi le point", lambda r: r["ia"] == 0 and "Nous sommes" in r["reponse"]),
    ("lecture", "lis-moi à voix haute l'article https://example.com",
     lambda r: r["ia"] == 0 and r["lecture_en_cours"]),
    ("arrêt lecture", "arrête la lecture", lambda r: r["ia"] == 0 and not r["lecture_en_cours"]),
    ("conversation", "salut, ça va ?", lambda r: r["ia"] == 1 and not r["outils"]),
    ("outil", "quel temps fait-il à Conakry ?",
     lambda r: any(o.startswith("get_weather") for o in r["outils"])),
    ("actualité", "quelle est la dernière version de Python ?", lambda r: "web_search" in r["outils"]),
    ("2 outils", "cherche la météo de Conakry puis enregistre-la dans le fichier {T}/meteo.txt",
     lambda r: any(o.startswith("get_weather") for o in r["outils"]) and "write_file" in r["outils"]),
    ("sensible", "supprime le fichier {T}/a_supprimer.txt",
     lambda r: "delete_file" in r["outils"] and r["confirmations"]),
    ("mémoire", "tu te souviens de ce qu'on a dit sur la météo ?",
     lambda r: not r["reponse"].startswith(("ERREUR", "EXCEPTION"))),
]
# Ces demandes ne doivent JAMAIS appeler l'IA (réponses instantanées partagées)
NO_AI = ("instantané", "briefing", "lecture", "arrêt lecture")
if "--sans-ia" in sys.argv:
    SCENARIOS = [s for s in SCENARIOS if s[0] in NO_AI]
INTERFACES = ("gui", "voix", "agent")
LABELS = {"gui": "Fenêtre", "voix": "Voix", "agent": "Terminal"}


def run_one(mode: str):
    """Déroule les scénarios dans CE processus pour une interface (une ligne JSON chacun)."""
    from dotenv import load_dotenv
    load_dotenv(".env")
    os.environ["AMAH_JOURNAL"] = "0"        # les tests n'écrivent pas dans ton journal
    T = os.path.join(tempfile.gettempdir(), "amah_banc_interfaces").replace("\\", "/")
    os.makedirs(T, exist_ok=True)
    open(f"{T}/a_supprimer.txt", "w", encoding="utf-8").write("fichier de test")
    if os.path.exists(f"{T}/meteo.txt"):
        os.remove(f"{T}/meteo.txt")

    import tools as tools_pkg
    from tools import TOOL_FUNCTIONS
    from tools.guard import guarded, set_confirm_handler
    tools_pkg.record_tool_use = lambda name: None
    stub = {
        "open_browser", "open_file", "speak", "play_music", "open_youtube", "open_steam",
        "open_epic_games", "launch_game_steam", "install_game_steam", "set_volume",
        "mute_audio", "set_brightness", "wifi_toggle", "kill_process", "run_command",
        "send_email", "draft_email", "send_notification", "set_reminder", "create_daily_task",
        "delete_task", "run_task_now", "start_auto_mute", "stop_auto_mute", "analyze_webcam",
        "listen", "listen_continuous", "screenshot_full", "take_screenshot", "click_element",
        "fill_form", "click_text", "type_in_field", "delete_file", "move_file",
        "organize_folder", "reset_stats", "write_clipboard", "read_clipboard", "delete_memory",
        "execute_plan", "run_code", "unzip_file", "zip_files", "edit_pdf", "save_memory",
    }
    write = {"write_file", "edit_file", "create_word", "create_pdf", "create_txt", "create_excel",
             "append_to_excel", "create_qrcode", "create_folder", "write_code"}
    calls, confirms = [], []

    def simulated(*a, **kw):
        return {"success": True, "simule": True}

    def wrap(n, f):
        fake = guarded(n, simulated)            # confirmation demandée comme en vrai

        @functools.wraps(f)
        def inner(*a, **kw):
            calls.append(n)
            if n in stub or (n in write and "amah_banc_interfaces" not in json.dumps(kw, ensure_ascii=False)):
                return fake(*a, **kw)
            return f(*a, **kw)
        return inner

    for n, f in list(TOOL_FUNCTIONS.items()):
        TOOL_FUNCTIONS[n] = wrap(n, f)

    import tools.reader as R
    R._worker = lambda chunks: R._stop.wait(60)     # lecture sans son

    from groq_client import GroqClient
    llm = {"appels": 0, "tokens": 0}
    real_chat = GroqClient.chat

    def counted(self, *a, **k):
        r = real_chat(self, *a, **k)
        llm["appels"] += 1
        try:
            llm["tokens"] += r.usage.total_tokens
        except Exception:
            pass
        return r
    GroqClient.chat = counted

    from config import SYSTEM_PROMPT

    def accept(name, args, description):
        confirms.append(name)
        return True

    if mode == "gui":
        import gui
        gui.save_message = lambda *a, **k: None
        shown = []

        class Root:
            def after(self, delay, fn=None, *args):
                if fn is not None and getattr(fn, "__name__", "") in (
                        "_show_reply", "_finish_streamed_reply", "_show_error"):
                    shown.append(args[0] if args else "")

        g = object.__new__(gui.AmahGUI)
        g.groq, g.root, g.session_id = GroqClient.get(), Root(), "banc"
        g.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        set_confirm_handler(accept)

        def send(q):
            g._tools_this_call = []
            g.messages.append({"role": "user", "content": q})
            shown.clear()
            g._run_chat()
            return shown[-1] if shown else "(aucune réponse affichée)"

    elif mode == "voix":
        import threading
        import voice_fullscreen as V
        V.save_message = lambda *a, **k: None

        class Fake:
            def after(self, *a, **k): pass
            def set(self, *a, **k): pass

        ui = object.__new__(V.AmahVoiceUI)
        ui.client, ui.root, ui._reply_var, ui.session_id = GroqClient.get(), Fake(), Fake(), "banc"
        ui.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        ui._pending_live_action, ui._live_mode = None, False
        ui._chat_lock = threading.Lock()
        set_confirm_handler(accept)

        def send(q):
            reply, err = ui._chat(q)
            return ("ERREUR " if err else "") + reply

    else:
        import agent
        from rich.console import Console
        builtins.input = lambda prompt="": (confirms.append("terminal"), "o")[1]
        client = agent._GroqClientAdapter()
        ctx = agent.ConversationContext()
        history = [{"role": "system", "content": SYSTEM_PROMPT}]

        def send(q):
            agent.console = Console(file=io.StringIO(), width=250)
            history.append({"role": "user", "content": q})
            ctx.ingest(q)
            r = agent.chat(client, history, ctx)
            history.append({"role": "assistant", "content": str(r)})
            return str(r)

    pause = float(os.environ.get("PAUSE", "15"))
    for name, q, _check in SCENARIOS:
        q = q.replace("{T}", T)
        calls.clear(); confirms.clear()
        before = dict(llm)
        t = time.time()
        try:
            reply = send(q)
        except Exception as e:
            reply = f"EXCEPTION {type(e).__name__}: {e}"
        print(json.dumps({
            "interface": mode, "test": name, "s": round(time.time() - t, 1),
            "ia": llm["appels"] - before["appels"], "tokens": llm["tokens"] - before["tokens"],
            "outils": calls[:6], "confirmations": confirms[:3], "lecture_en_cours": R.is_reading(),
            "reponse": re.sub(r"\s+", " ", str(reply))[:260],
        }, ensure_ascii=False), flush=True)
        time.sleep(pause if llm["appels"] > before["appels"] else 1)
    if R.is_reading():
        R.stop_reading()


def main():
    if "--run" in sys.argv:
        run_one(sys.argv[sys.argv.index("--run") + 1])
        return 0
    chosen = INTERFACES
    if "--interface" in sys.argv:
        chosen = (sys.argv[sys.argv.index("--interface") + 1],)
    results = {}
    for i, mode in enumerate(chosen):
        if i and "--sans-ia" not in sys.argv:
            time.sleep(30)                      # laisse les quotas par minute se vider
        print(f"… {LABELS[mode]} en cours", flush=True)
        extra = ["--sans-ia"] if "--sans-ia" in sys.argv else []
        proc = subprocess.run([sys.executable, "-m", "benchmarks.benchmark_interfaces", "--run", mode] + extra,
                              capture_output=True, text=True, encoding="utf-8",
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        rows = {}
        for line in proc.stdout.splitlines():
            if line.startswith("{"):
                row = json.loads(line)
                rows[row["test"]] = row
        if proc.returncode and not rows:
            print(proc.stderr[-1500:])
        results[mode] = rows

    print(f"\n{'':15}" + "".join(f"{LABELS[m]:>11}" for m in chosen))
    total = ok = 0
    for name, _q, check in SCENARIOS:
        line = f"{name:15}"
        for mode in chosen:
            row = results[mode].get(name)
            good = bool(row) and bool(check(row))
            total += 1
            ok += good
            line += f"{('OK' if good else 'ECHEC'):>11}"
        print(line)
    print("\ntokens :" + "".join(
        f"  {LABELS[m]} {sum(r['tokens'] for r in results[m].values()):,}".replace(",", " ") for m in chosen))
    for mode in chosen:
        for name, _q, check in SCENARIOS:
            row = results[mode].get(name)
            if not row or not check(row):
                print(f"  ÉCHEC {LABELS[mode]} / {name} : {row['reponse'][:150] if row else '(pas de résultat)'}")
    print(f"\n{ok}/{total} vérifications réussies")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
