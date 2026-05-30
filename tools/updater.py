"""
Système de mise à jour automatique d'Amah Agent.
Vérifie si une nouvelle version est disponible et la télécharge.
"""
import sys
import urllib.request
import json
import subprocess
import threading
from pathlib import Path

CURRENT_VERSION = "1.0.0"

# URL où tu héberges les infos de version — à mettre à jour avant distribution
# Format du fichier JSON attendu :
# {"version": "1.1.0", "url": "https://ton-site.com/dist/Amah Agent.exe", "notes": "Corrections de bugs"}
VERSION_URL = "https://raw.githubusercontent.com/ton-compte/amah-agent/main/version.json"

_URL_IS_PLACEHOLDER = "ton-compte" in VERSION_URL


def check_update() -> dict:
    """Vérifie si une mise à jour est disponible."""
    if _URL_IS_PLACEHOLDER:
        return {
            "success": False,
            "message": "Mises à jour non configurées. Héberge un version.json et mets à jour VERSION_URL dans tools/updater.py.",
        }
    try:
        req  = urllib.request.Request(VERSION_URL, headers={"User-Agent": "AmahAgent/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=8).read())

        latest   = data.get("version", "0.0.0")
        url      = data.get("url", "")
        notes    = data.get("notes", "")

        if _version_newer(latest, CURRENT_VERSION):
            return {
                "success":          True,
                "mise_a_jour":      True,
                "version_actuelle": CURRENT_VERSION,
                "nouvelle_version": latest,
                "notes":            notes,
                "url":              url,
            }
        return {
            "success":          True,
            "mise_a_jour":      False,
            "version_actuelle": CURRENT_VERSION,
            "message":          "Amah est a jour.",
        }
    except Exception as e:
        return {"error": f"Impossible de verifier les mises a jour : {e}"}


def download_update(url: str) -> dict:
    """Télécharge et installe la mise à jour."""
    try:
        if not getattr(sys, 'frozen', False):
            return {"error": "La mise a jour n'est disponible que pour la version .exe"}

        exe_path = Path(sys.executable)
        tmp_path = exe_path.parent / "Amah Agent_new.exe"

        def _download():
            urllib.request.urlretrieve(url, str(tmp_path))
            # Script PowerShell pour remplacer le .exe après fermeture
            script = f"""
Start-Sleep -Seconds 3
Remove-Item -Force '{exe_path}'
Rename-Item -Path '{tmp_path}' -NewName '{exe_path.name}'
Start-Process '{exe_path}'
"""
            ps_path = exe_path.parent / "_update.ps1"
            ps_path.write_text(script)
            subprocess.Popen(
                ["powershell", "-NoProfile", "-File", str(ps_path)],
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        threading.Thread(target=_download, daemon=True).start()
        return {"success": True, "message": "Telechargement en cours... Amah se relancera automatiquement."}
    except Exception as e:
        return {"error": str(e)}


def get_current_version() -> dict:
    """Retourne la version actuelle d'Amah."""
    return {"success": True, "version": CURRENT_VERSION}


def _version_newer(v1: str, v2: str) -> bool:
    """Retourne True si v1 est plus récente que v2."""
    try:
        return tuple(int(x) for x in v1.split(".")) > tuple(int(x) for x in v2.split("."))
    except Exception:
        return False
