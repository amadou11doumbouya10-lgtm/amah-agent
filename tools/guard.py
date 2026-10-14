"""Garde-fou central des actions sensibles.

Toutes les interfaces (gui.py, voice_fullscreen.py + mode Live Gemini, agent.py,
execute_plan) appellent les outils via TOOL_FUNCTIONS. Les outils sensibles y
sont enveloppes par guarded() : avant d'agir, ils demandent l'accord de
l'utilisateur via le gestionnaire enregistre par l'interface active
(set_confirm_handler). Sans gestionnaire enregistre, l'action est refusee.

Avant ce module, gui.py et le mode vocal n'avaient aucune confirmation reelle :
seul le prompt demandait au modele de "confirmer", et une suppression ou une
commande destructive s'executait directement.
"""
import functools
import inspect
import threading
from pathlib import Path

# Outils qui suppriment, deplacent, executent, envoient ou changent la config.
SENSITIVE_TOOLS = {
    "run_command", "run_code", "delete_file", "move_file", "organize_folder",
    "edit_file", "edit_pdf", "kill_process", "wifi_toggle", "send_email",
    "install_game_steam", "create_daily_task", "delete_task", "run_task_now",
    "delete_memory", "reset_stats", "start_auto_mute",
}

# open_file sur ces extensions lance un programme au lieu d'ouvrir un document.
_EXECUTABLE_EXT = {
    ".exe", ".bat", ".cmd", ".com", ".ps1", ".vbs", ".vbe", ".js", ".jse",
    ".msi", ".lnk", ".scr", ".py", ".pyw", ".jar", ".hta", ".reg", ".wsf",
}

_handler = None


def set_confirm_handler(handler):
    """Enregistre la fonction handler(name, args, description) -> bool."""
    global _handler
    _handler = handler


def needs_confirmation(name: str, args: dict) -> bool:
    if name == "run_command":
        # Une commande que le filtre bloquera de toute facon n'est pas soumise a
        # l'utilisateur : lui demander "Oui" pour un refus garanti est trompeur.
        from tools.system import _blocked_reason
        return _blocked_reason(str(args.get("command") or "")) is None
    if name in SENSITIVE_TOOLS:
        return True
    if name == "write_file":
        # Creer un fichier : libre. Ecraser un fichier existant : confirmation.
        return _exists(args.get("path"))
    if name == "open_file":
        return Path(str(args.get("path") or "")).suffix.lower() in _EXECUTABLE_EXT
    # execute_plan n'est pas filtre ici : chacune de ses etapes passe par
    # TOOL_FUNCTIONS et demande donc sa propre confirmation.
    return False


def _exists(path) -> bool:
    try:
        return bool(path) and Path(str(path)).expanduser().exists()
    except Exception:
        return False


def describe(name: str, args: dict) -> str:
    """Phrase lisible decrivant l'action, affichee dans la confirmation."""
    a = lambda key: str(args.get(key) or "").strip()
    descriptions = {
        "run_command": lambda: f"Exécuter la commande : {a('command')}",
        "run_code": lambda: f"Exécuter le script : {a('path')}",
        "delete_file": lambda: f"Supprimer : {a('path')}",
        "move_file": lambda: f"Déplacer {a('source')} vers {a('destination')}",
        "organize_folder": lambda: f"Ranger (déplacer) les fichiers du dossier : {a('path')}",
        "edit_file": lambda: f"Modifier le fichier : {a('path')}",
        "edit_pdf": lambda: f"Modifier le PDF : {a('path')}",
        "write_file": lambda: f"Remplacer le contenu du fichier existant : {a('path')}",
        "open_file": lambda: f"Lancer le programme : {a('path')}",
        "kill_process": lambda: f"Fermer le processus : {a('name') or a('pid')}",
        "wifi_toggle": lambda: "Activer le wifi" if args.get("enable", True) else "Désactiver le wifi",
        "send_email": lambda: f"Envoyer un email à {a('to')} (sujet : {a('subject')})",
        "install_game_steam": lambda: f"Installer le jeu : {a('game_name')}",
        "create_daily_task": lambda: f"Créer la tâche planifiée « {a('name')} » : {a('command')}",
        "delete_task": lambda: f"Supprimer la tâche planifiée : {a('name')}",
        "run_task_now": lambda: f"Lancer la tâche planifiée : {a('name')}",
        "delete_memory": lambda: f"Supprimer le souvenir n°{a('memory_id')}",
        "reset_stats": lambda: "Effacer toutes les statistiques d'utilisation",
        "start_auto_mute": lambda: "Activer la webcam pour couper le son automatiquement",
    }
    builder = descriptions.get(name)
    return builder() if builder else f"Utiliser l'outil {name}"


def guarded(name: str, func):
    """Enveloppe func pour demander confirmation quand l'action est sensible."""
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        signature = None

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            named = dict(signature.bind_partial(*args, **kwargs).arguments) if signature else dict(kwargs)
        except TypeError:
            named = dict(kwargs)
        if needs_confirmation(name, named):
            description = describe(name, named)
            try:
                allowed = bool(_handler and _handler(name, named, description))
            except Exception:
                allowed = False
            if not allowed:
                return {
                    "error": f"Action annulée, l'utilisateur ne l'a pas autorisée : {description}",
                    "refuse": True,
                }
        return func(*args, **kwargs)

    return wrapper


def tk_confirm_handler(root, timeout: float = 120.0):
    """Gestionnaire pour les interfaces tkinter : boite Oui/Non sur le thread Tk.

    Les outils tournent dans un thread de travail ; tkinter ne doit etre touche
    que depuis le thread principal, d'ou root.after + Event. Sans reponse dans
    le delai, l'action est refusee.
    """
    from tkinter import messagebox

    def ask(description: str) -> bool:
        return messagebox.askyesno(
            "Amah demande ton accord",
            f"{description}\n\nAutoriser cette action ?",
            icon="warning", default="no", parent=root,
        )

    def handler(name, args, description) -> bool:
        if threading.current_thread() is threading.main_thread():
            return ask(description)
        done = threading.Event()
        result = [False]

        def run():
            try:
                result[0] = ask(description)
            finally:
                done.set()

        root.after(0, run)
        done.wait(timeout)
        return result[0]

    return handler
