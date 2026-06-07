import os
import subprocess
import platform
from pathlib import Path

# Commandes autorisées — sécurité
BLOCKED_KEYWORDS = [
    "rm -rf", "del /f /s", "format", "rmdir /s", "shutdown",
    "net user", "reg delete", "cipher", "diskpart",
    "invoke-expression", "iex ", "downloadstring", "webclient",
    "start-process", "invoke-webrequest", "curl -s", "wget ",
    "remove-item -recurse", "remove-item -r", "rd /s",
]

BLOCKED_PATTERNS = [
    "&",   # chaining de commandes
    "&&",
    "||",
    "`",   # backtick exécution
    "$(", # sous-expression
]


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
    cmd_lower = command.lower()
    for blocked in BLOCKED_KEYWORDS:
        if blocked in cmd_lower:
            return {"error": f"Commande bloquee pour securite : contient '{blocked}'"}
    for pattern in BLOCKED_PATTERNS:
        if pattern in command:
            return {"error": f"Caractere interdit dans la commande : '{pattern}'"}

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
