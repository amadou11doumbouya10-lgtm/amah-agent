"""Vérifie le garde-fou des actions sensibles (tools/guard.py) — sans appel API.

Lancer depuis la racine du projet :
    py -3.13 -m benchmarks.benchmark_guard

Travaille dans un dossier temporaire ; ne lance aucun programme (les chemins
d'exécutables testés n'existent pas). Ouvre une fenêtre Tk invisible pour
vérifier la boîte Oui/Non appelée depuis un thread de travail.
Code de sortie 1 si une vérification échoue.
"""
import builtins
import io
import json
import os
import sys
import tempfile
import threading

import tools
from tools import TOOL_FUNCTIONS as T
from tools import guard

# Ne pas compter les appels du test dans les statistiques réelles (get_stats)
tools.record_tool_use = lambda name: None

results = []


def check(label, condition):
    results.append(bool(condition))
    print(("OK    " if condition else "ECHEC ") + label)


def main(folder: str):
    def make(name, text="x"):
        path = os.path.join(folder, name).replace("\\", "/")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    # 1. Sans gestionnaire : refus par défaut
    guard.set_confirm_handler(None)
    a = make("a.txt")
    r = T["delete_file"](path=a)
    check("sans interface : suppression refusée", r.get("refuse") and os.path.exists(a))

    # 2. Refus puis accord
    asked = []
    guard.set_confirm_handler(lambda n, args, d: asked.append(d) or False)
    r = T["delete_file"](path=a)
    check("refus : fichier conservé", r.get("refuse") and os.path.exists(a))
    check("description lisible", asked and asked[-1].startswith("Supprimer"))
    guard.set_confirm_handler(lambda n, args, d: True)
    r = T["delete_file"](path=a)
    check("accord : fichier supprimé", r.get("success") and not os.path.exists(a))

    # 3. write_file : création libre, écrasement confirmé
    asked.clear()
    guard.set_confirm_handler(lambda n, args, d: asked.append(d) or False)
    new = os.path.join(folder, "nouveau.txt").replace("\\", "/")
    r = T["write_file"](path=new, content="1")
    check("write_file nouveau fichier : sans question", r.get("success") and not asked)
    r = T["write_file"](path=new, content="2")
    with open(new, encoding="utf-8") as f:
        check("write_file existant : question posée, refus respecté", r.get("refuse") and f.read() == "1")

    # 4. open_file : exécutable confirmé, document non
    asked.clear()
    r = T["open_file"](path=os.path.join(folder, "inexistant.exe"))
    check("open_file .exe : question posée", r.get("refuse") and asked)
    asked.clear()
    r = T["open_file"](path=os.path.join(folder, "inexistant.txt"))
    check("open_file .txt : pas de question", not asked and "introuvable" in str(r.get("error", "")).lower())

    # 5. Outil non sensible, appel positionnel, commande déjà bloquée
    asked.clear()
    check("calculate : pas de question", T["calculate"](expression="2+2").get("success") and not asked)
    b = make("b.txt")
    check("appel positionnel : toujours filtré", T["delete_file"](b).get("refuse") and os.path.exists(b))
    asked.clear()
    r = T["run_command"](command="rm C:/Users/test -Recurse -Force")
    check("commande dangereuse : bloquée sans question", not asked and "bloquée" in str(r.get("error", "")))

    # 6. Boîte Tk appelée depuis un thread de travail
    import tkinter as tk
    from tkinter import messagebox
    seen = {}

    def fake_ask(title, message, **kwargs):
        seen["main_thread"] = threading.current_thread() is threading.main_thread()
        return True

    real_ask = messagebox.askyesno
    messagebox.askyesno = fake_ask
    root = tk.Tk()
    root.withdraw()
    guard.set_confirm_handler(guard.tk_confirm_handler(root))
    out = {}

    def worker():
        out["r"] = T["delete_file"](path=b)
        root.after(0, root.quit)

    threading.Thread(target=worker, daemon=True).start()
    root.after(10000, root.quit)
    root.mainloop()
    root.destroy()
    messagebox.askyesno = real_ask
    check("Tk : boîte affichée sur le thread principal", seen.get("main_thread") is True)
    check("Tk : accord appliqué depuis le thread de travail",
          out.get("r", {}).get("success") and not os.path.exists(b))

    # 7. Terminal : une seule question pour un outil confirmé par Security V0.2
    from rich.console import Console
    import agent
    agent.console = Console(file=io.StringIO())
    prompts = []
    real_input = builtins.input
    builtins.input = lambda prompt="": prompts.append(prompt) or "o"
    try:
        c = make("c.txt")
        res = json.loads(agent._execute_tool_by_name("delete_file", {"path": c}))
        check("terminal : une seule question et suppression faite", len(prompts) == 1 and res.get("success"))
        prompts.clear()
        agent._execute_tool_by_name("open_file", {"path": os.path.join(folder, "x.exe")})
        check("terminal : open_file .exe demande confirmation", len(prompts) == 1)
    finally:
        builtins.input = real_input


def check_clicks():
    """Sites web : un clic qui envoie, paie ou supprime demande l'accord
    (le modèle a cliqué "Envoyer ma candidature" avant de remplir, 19/10/2026)."""
    from tools.guard import needs_confirmation
    sending = ["Envoyer ma candidature", "Valider la commande", "Payer", "Supprimer le produit",
               "S'inscrire", "Confirmer"]
    browsing = ["Devenir vendeur", "Connexion", "Mode et accessoires", "Choisir le pays", "Voir la boutique"]
    check("clic Envoyer / Payer / Supprimer… : confirmation",
          all(needs_confirmation("click_text", {"text": t}) for t in sending)
          and needs_confirmation("click_element", {"selector": "button[type=submit]"}))
    check("clic de navigation (Devenir vendeur, Connexion, pays…) : libre",
          not any(needs_confirmation("click_text", {"text": t}) for t in browsing))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="amah_guard_") as tmp:
        main(tmp)
    check_clicks()
    print(f"\n{sum(results)}/{len(results)} vérifications réussies")
    sys.exit(0 if all(results) else 1)
