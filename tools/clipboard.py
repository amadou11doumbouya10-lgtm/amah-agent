import os
import subprocess


def read_clipboard() -> dict:
    """Lit le contenu actuel du presse-papiers."""
    try:
        # Sortie forcée en UTF-8 : décodée en cp1252, un "✓" ou un emoji
        # faisait planter la lecture
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Console]::OutputEncoding = [Text.Encoding]::UTF8; Get-Clipboard -Raw"],
            capture_output=True, timeout=5,
        )
        content = r.stdout.decode("utf-8", errors="replace").strip()
        return {"success": True, "contenu": content, "longueur": len(content)}
    except Exception as e:
        return {"error": str(e)}


def write_clipboard(text: str) -> dict:
    """Copie un texte dans le presse-papiers."""
    try:
        # Texte passé par variable d'environnement, jamais dans le code : avec
        # Set-Clipboard -Value "<texte>", un "$(commande)" ou un guillemet
        # ("\"" n'échappe rien en PowerShell) exécutait du code (testé).
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $env:AMAH_CLIP_TEXT"],
            capture_output=True, timeout=5,
            env={**os.environ, "AMAH_CLIP_TEXT": str(text or "")},
        )
        if r.returncode != 0:
            return {"error": (r.stderr or b"").decode(errors="replace").strip() or "Copie impossible"}
        return {"success": True, "copie": str(text)[:100]}
    except Exception as e:
        return {"error": str(e)}
