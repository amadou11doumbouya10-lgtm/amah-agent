import os
import subprocess
import platform
from pathlib import Path

# Commandes autorisées — sécurité
BLOCKED_KEYWORDS = [
    "rm -rf", "del /f", "format", "rmdir /s", "shutdown",
    "net user", "reg delete", "cipher", "diskpart"
]


def get_system_info() -> dict:
    try:
        import psutil
        ram       = psutil.virtual_memory()
        disk      = psutil.disk_usage("C:\\")
        cpu_count = psutil.cpu_count()
        cpu_pct   = psutil.cpu_percent(interval=1)

        return {
            "success":      True,
            "os":           f"{platform.system()} {platform.release()} {platform.version()[:30]}",
            "python":       platform.python_version(),
            "cpu":          f"{cpu_count} cœurs — {cpu_pct}% utilisé",
            "ram_totale":   _fmt(ram.total),
            "ram_utilisée": _fmt(ram.used),
            "ram_libre":    _fmt(ram.available),
            "disque_total": _fmt(disk.total),
            "disque_libre": _fmt(disk.free),
            "disque_utilisé": f"{disk.percent}%",
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
            return {"error": f"Commande bloquée pour sécurité : contient '{blocked}'"}

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


def _fmt(size: int) -> str:
    for unit in ["o", "Ko", "Mo", "Go"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} To"
