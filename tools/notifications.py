import os
import subprocess
import threading
import time

# Le titre et le texte passent par des variables d'environnement, jamais dans
# le code du script : PowerShell traite aussi ’ ‘ comme des apostrophes, et un
# sujet d'email piégé ("Facture’; <commande>; ‘") exécutait du code (testé).
_NOTIFY_PS = """
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Application
$n.BalloonTipIcon  = [System.Windows.Forms.ToolTipIcon]::Info
$n.BalloonTipTitle = $env:AMAH_NOTIF_TITLE
$n.BalloonTipText  = $env:AMAH_NOTIF_TEXT
$n.Visible = $true
$n.ShowBalloonTip([int]$env:AMAH_NOTIF_MS)
Start-Sleep -Milliseconds ([int]$env:AMAH_NOTIF_MS + 2000)
$n.Dispose()
"""


def send_notification(title: str, message: str, duration: int = 5) -> dict:
    """
    Affiche une notification ballon Windows (coin bas droite).
    Aucune dépendance externe — utilise Windows Forms via PowerShell.
    """
    try:
        try:
            seconds = max(1, min(60, int(duration)))
        except (TypeError, ValueError):
            seconds = 5
        env = {**os.environ,
               # Une bulle Windows tronque au-delà de ~250 caractères
               "AMAH_NOTIF_TITLE": str(title or "Amah")[:60],
               "AMAH_NOTIF_TEXT": str(message or " ")[:250],
               "AMAH_NOTIF_MS": str(seconds * 1000)}
        threading.Thread(
            target=lambda: subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", _NOTIFY_PS],
                creationflags=subprocess.CREATE_NO_WINDOW, env=env,
            ),
            daemon=True
        ).start()
        return {"success": True, "notification": f"{title} — {message}"}
    except Exception as e:
        return {"error": str(e)}


def set_reminder(message: str, minutes: int = 5) -> dict:
    """
    Programme un rappel dans X minutes — notification Windows automatique.
    """
    try:
        def _remind():
            time.sleep(minutes * 60)
            send_notification("Rappel Amah", message, duration=10)

        threading.Thread(target=_remind, daemon=True).start()
        return {
            "success": True,
            "message": f"Rappel programme dans {minutes} minute(s) : {message}"
        }
    except Exception as e:
        return {"error": str(e)}
