"""
Outils code — write_code, run_code, explain_code
"""
import subprocess
import sys
from pathlib import Path

_ALLOWED_RUN = {".py", ".js"}
_RUNNER = {
    ".py":  [sys.executable],
    ".js":  ["node"],
}


def write_code(filename: str, code: str, language: str = "") -> dict:
    """Écrit du code dans un fichier (Python, JS, HTML, CSS, etc.) et le crée si besoin."""
    p = Path(filename).expanduser()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(code, encoding="utf-8")
        lines = len(code.splitlines())
        lang  = language or p.suffix.lstrip(".") or "texte"
        return {
            "success": True,
            "fichier": str(p),
            "langage": lang,
            "lignes":  lines,
            "taille":  f"{p.stat().st_size} octets",
        }
    except Exception as e:
        return {"error": str(e)}


def run_code(path: str) -> dict:
    """Exécute un fichier Python ou JavaScript et retourne la sortie (timeout 30s)."""
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"Fichier introuvable : {path}"}

    ext = p.suffix.lower()
    if ext not in _ALLOWED_RUN:
        return {"error": f"Extension '{ext}' non supportée. Seuls .py et .js sont autorisés."}

    runner = _RUNNER[ext]
    try:
        result = subprocess.run(
            runner + [str(p)],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if len(stdout) > 2000:
            stdout = stdout[:2000] + "\n[... sortie tronquée ...]"

        return {
            "success":     result.returncode == 0,
            "fichier":     p.name,
            "sortie":      stdout or "(aucune sortie)",
            "erreurs":     stderr[:500] if stderr else None,
            "code_retour": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Timeout 30s dépassé — le script est trop long."}
    except FileNotFoundError:
        runner_name = runner[0]
        return {"error": f"Interpréteur '{runner_name}' introuvable. Vérifie ton installation."}
    except Exception as e:
        return {"error": str(e)}


def explain_code(path: str) -> dict:
    """Lit un fichier de code pour que l'IA l'analyse et l'explique."""
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"Fichier introuvable : {path}"}
    try:
        code = p.read_text(encoding="utf-8", errors="replace")
        if len(code) > 5000:
            code = code[:5000] + "\n\n[... tronqué à 5000 caractères ...]"
        return {
            "success":     True,
            "fichier":     p.name,
            "extension":   p.suffix,
            "lignes":      len(code.splitlines()),
            "code":        code,
            "instruction": "Explique ce code de façon claire : rôle global, fonctions principales, points importants.",
        }
    except Exception as e:
        return {"error": str(e)}
