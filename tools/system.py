import os
import re
import subprocess
import platform
from pathlib import Path

# Sécurité run_command : commandes refusées quel que soit l'ordre des arguments.
# Les anciennes sous-chaînes ("remove-item -recurse", "format"...) laissaient
# passer les alias (rm, ri, iwr, irm...) et "-Path X -Recurse", et bloquaient
# à tort "Get-Date -Format". Les suppressions/kill/tâches ont leurs propres
# outils (delete_file, kill_process, create_daily_task) soumis à confirmation.
_W = r"(?<![\w-])"   # début de mot de commande (pas au milieu d'un nom ou d'une option)
_E = r"(?![\w-])"    # fin de mot de commande
BLOCKED_REGEX = [
    (_W + r"(remove-item|ri|rm|rmdir|rd|del|erase|clear-content|clc|clear-recyclebin)" + _E,
     "suppression de fichiers (utilise delete_file)"),
    (_W + r"(format-volume|clear-disk|initialize-disk|diskpart|mkfs)" + _E + r"|" + _W + r"format\s+[a-z]:",
     "formatage de disque"),
    (_W + r"(stop-computer|restart-computer|shutdown|logoff)" + _E, "extinction ou redémarrage"),
    (_W + r"(invoke-expression|iex|invoke-command|icm|add-type)" + _E + r"|scriptblock|-enc(odedcommand)?" + _E
     + r"|frombase64string", "exécution de code dynamique"),
    (_W + r"(invoke-webrequest|iwr|invoke-restmethod|irm|curl|wget|start-bitstransfer|bitsadmin|certutil)" + _E
     + r"|downloadstring|downloadfile|net\.webclient", "téléchargement"),
    (_W + r"(start-process|saps|start|invoke-item|ii|rundll32|mshta|wscript|cscript|regsvr32)" + _E,
     "lancement de programme (utilise open_file)"),
    (_W + r"(powershell|pwsh|cmd)(\.exe)?" + _E, "shell imbriqué"),
    (_W + r"(stop-process|spps|kill|taskkill)" + _E, "arrêt de processus (utilise kill_process)"),
    (_W + r"(set-mppreference|add-mppreference|set-executionpolicy|bcdedit|vssadmin|wbadmin|cipher|takeown|icacls)" + _E,
     "sécurité du système"),
    (_W + r"reg(\.exe)?\s+(delete|add|import)" + _E
     + r"|" + _W + r"(remove-itemproperty|set-itemproperty|new-itemproperty)" + _E, "registre Windows"),
    (_W + r"net(\.exe)?\s+(user|localgroup)" + _E + r"|netsh\s+advfirewall", "comptes ou pare-feu"),
    (_W + r"(stop-service|set-service|remove-service|schtasks|register-scheduledtask|unregister-scheduledtask)" + _E
     + r"|" + _W + r"sc(\.exe)?\s+(delete|stop|config)" + _E, "services ou tâches planifiées"),
]

BLOCKED_OPERATORS = [
    "&",   # opérateur d'appel / enchaînement
    "||",
    "`",   # échappement PowerShell
    "$(",  # sous-expression
]


def _blocked_reason(command: str):
    """Retourne la raison du blocage, ou None si la commande est acceptée."""
    for pattern, reason in BLOCKED_REGEX:
        if re.search(pattern, command, flags=re.IGNORECASE):
            return reason
    for operator in BLOCKED_OPERATORS:
        if operator in command:
            return f"caractère interdit « {operator} »"
    return None


def get_system_info() -> dict:
    try:
        import psutil
        ram       = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()
        cpu_pct   = psutil.cpu_percent(interval=1)

        disques = {}
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disques[part.mountpoint] = f"{_fmt(usage.free)} libres / {_fmt(usage.total)} ({usage.percent}% utilisé)"
            except (PermissionError, OSError):
                pass

        return {
            "success":      True,
            "os":           f"{platform.system()} {platform.release()} {platform.version()[:30]}",
            "python":       platform.python_version(),
            "cpu":          f"{cpu_count} cœurs — {cpu_pct}% utilisé",
            "ram_totale":   _fmt(ram.total),
            "ram_utilisée": _fmt(ram.used),
            "ram_libre":    _fmt(ram.available),
            "disques":      disques,
        }
    except ImportError:
        # Fallback sans psutil
        return {
            "success": True,
            "os":      f"{platform.system()} {platform.release()}",
            "python":  platform.python_version(),
            "note":    "Installe psutil pour plus de détails : pip install psutil",
        }
    except Exception as e:
        return {"error": str(e)}


def open_file(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"Chemin introuvable : {path}"}
    try:
        os.startfile(str(p))
        return {"success": True, "ouvert": str(p)}
    except Exception as e:
        return {"error": str(e)}


def run_command(command: str) -> dict:
    reason = _blocked_reason(command)
    if reason:
        return {"error": f"Commande bloquée pour sécurité : {reason}."}

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace"
        )
        output = result.stdout.strip() or result.stderr.strip()
        if len(output) > 3000:
            output = output[:3000] + "\n[... sortie tronquée ...]"

        return {
            "success":     result.returncode == 0,
            "commande":    command,
            "sortie":      output,
            "code_retour": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Commande trop longue (timeout 30s)"}
    except Exception as e:
        return {"error": str(e)}


_BLOCKED_PROCS = {
    "lsass.exe","csrss.exe","winlogon.exe","smss.exe","wininit.exe",
    "services.exe","svchost.exe","system","registry","explorer.exe",
}

def kill_process(name: str = "", pid: int = 0) -> dict:
    """Termine un processus Windows par nom ou PID. Bloque les processus système critiques."""
    try:
        import psutil
    except ImportError:
        return {"error": "psutil manquant. Lance : pip install psutil"}

    if not name and not pid:
        return {"error": "Fournis un nom ou un PID."}

    killed = []
    not_found = True

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            proc_name = proc.info["name"] or ""
            proc_pid  = proc.info["pid"]

            match = (pid and proc_pid == pid) or (name and name.lower() in proc_name.lower())
            if not match:
                continue

            not_found = False
            if proc_name.lower() in _BLOCKED_PROCS:
                return {"error": f"Impossible de terminer '{proc_name}' — processus système protégé."}

            proc.terminate()
            killed.append(f"{proc_name} (PID {proc_pid})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        except Exception:
            pass

    if not_found:
        return {"error": f"Aucun processus '{name or pid}' trouvé."}
    return {"success": True, "termines": killed}


def _fmt(size: int) -> str:
    for unit in ["o", "Ko", "Mo", "Go"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} To"
