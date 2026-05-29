"""
Gestion du Planificateur de tâches Windows.
Les tâches s'exécutent même quand Amah est fermée.
"""
import subprocess
import json
from pathlib import Path
import sys


def _ps(command: str) -> tuple:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True, text=True, timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def create_daily_task(name: str, command: str, hour: int = 8, minute: int = 0) -> dict:
    """
    Crée une tâche planifiée quotidienne dans le Planificateur Windows.
    name    : nom unique de la tâche
    command : commande PowerShell à exécuter
    hour    : heure (0-23)
    minute  : minute (0-59)
    """
    try:
        time_str = f"{hour:02d}:{minute:02d}"
        ps = f"""
$action  = New-ScheduledTaskAction -Execute 'powershell' -Argument '-NoProfile -WindowStyle Hidden -Command "{command}"'
$trigger = New-ScheduledTaskTrigger -Daily -At '{time_str}'
$settings = New-ScheduledTaskSettingsSet -RunOnlyIfNetworkAvailable:$false -StartWhenAvailable
Register-ScheduledTask -TaskName 'Amah_{name}' -Action $action -Trigger $trigger -Settings $settings -Force
"""
        out, err, code = _ps(ps)
        if code == 0:
            return {"success": True, "tache": f"Amah_{name}", "heure": time_str}
        return {"error": err or "Erreur inconnue"}
    except Exception as e:
        return {"error": str(e)}


def list_tasks() -> dict:
    """Liste toutes les tâches Amah planifiées."""
    try:
        out, _, _ = _ps("Get-ScheduledTask | Where-Object {$_.TaskName -like 'Amah_*'} | Select-Object TaskName, State | ConvertTo-Json")
        if not out or out == "null":
            return {"success": True, "taches": [], "total": 0}
        tasks = json.loads(out)
        if isinstance(tasks, dict):
            tasks = [tasks]
        return {"success": True, "taches": tasks, "total": len(tasks)}
    except Exception as e:
        return {"error": str(e)}


def delete_task(name: str) -> dict:
    """Supprime une tâche planifiée Amah."""
    try:
        task_name = name if name.startswith("Amah_") else f"Amah_{name}"
        out, err, code = _ps(f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false")
        if code == 0:
            return {"success": True, "supprimee": task_name}
        return {"error": err or "Tâche introuvable"}
    except Exception as e:
        return {"error": str(e)}


def run_task_now(name: str) -> dict:
    """Lance immédiatement une tâche planifiée."""
    try:
        task_name = name if name.startswith("Amah_") else f"Amah_{name}"
        out, err, code = _ps(f"Start-ScheduledTask -TaskName '{task_name}'")
        if code == 0:
            return {"success": True, "lancee": task_name}
        return {"error": err}
    except Exception as e:
        return {"error": str(e)}
