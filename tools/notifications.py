import subprocess
import threading
import time


def send_notification(title: str, message: str, duration: int = 5) -> dict:
    """
    Affiche une notification ballon Windows (coin bas droite).
    Aucune dépendance externe — utilise Windows Forms via PowerShell.
    """
    try:
        t = title.replace("'", " ")
        m = message.replace("'", " ")
        ps = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Application
$n.BalloonTipIcon  = [System.Windows.Forms.ToolTipIcon]::Info
$n.BalloonTipTitle = '{t}'
$n.BalloonTipText  = '{m}'
$n.Visible = $true
$n.ShowBalloonTip({duration * 1000})
Start-Sleep -Seconds {duration + 2}
$n.Dispose()
"""
        threading.Thread(
            target=lambda: subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                creationflags=subprocess.CREATE_NO_WINDOW
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
