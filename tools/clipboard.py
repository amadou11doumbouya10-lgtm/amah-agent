import subprocess


def read_clipboard() -> dict:
    """Lit le contenu actuel du presse-papiers."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5
        )
        content = r.stdout.strip()
        return {"success": True, "contenu": content, "longueur": len(content)}
    except Exception as e:
        return {"error": str(e)}


def write_clipboard(text: str) -> dict:
    """Copie un texte dans le presse-papiers."""
    try:
        safe = text.replace('"', '\\"')
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f'Set-Clipboard -Value "{safe}"'],
            capture_output=True, timeout=5
        )
        return {"success": True, "copie": text[:100]}
    except Exception as e:
        return {"error": str(e)}
