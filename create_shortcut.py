"""
Lance ce script une seule fois pour créer le raccourci Amah sur le bureau.
    py -3.13 create_shortcut.py
"""
import sys
import subprocess
from pathlib import Path


def main():
    project   = Path(__file__).parent.absolute()
    gui_path  = project / "gui.py"
    icon_path = project / "amah.ico"
    desktop   = Path.home() / "Desktop"
    shortcut  = desktop / "Amah Agent.lnk"
    # pythonw.exe au lieu de python.exe — pas de fenêtre console noire
    python    = sys.executable.replace("python.exe", "pythonw.exe")

    icon_line = f"$lnk.IconLocation = '{icon_path}'" if icon_path.exists() else ""

    script = f"""
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut('{shortcut}')
$lnk.TargetPath = '{python}'
$lnk.Arguments = '"{gui_path}"'
$lnk.WorkingDirectory = '{project}'
$lnk.Description = 'The Amah — Agent IA Local'
$lnk.WindowStyle = 1
{icon_line}
$lnk.Save()
"""

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print(f"Raccourci créé sur le bureau : {shortcut}")
        print("Double-clique dessus pour lancer Amah.")
    else:
        print(f"Erreur lors de la création du raccourci :")
        print(result.stderr)


if __name__ == "__main__":
    main()
