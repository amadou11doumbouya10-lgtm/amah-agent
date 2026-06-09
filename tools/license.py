"""
Système de licence offline pour Amah Agent.
La clé est liée à l'identifiant unique de la machine Windows.

Pour générer une clé client : py -3.13 tools/license.py <machine_id>
"""
import hashlib
import hmac
import subprocess
import sys
import os

def _get_secret() -> bytes:
    """Lit le secret de licence depuis .env -- AUCUNE valeur par défaut :
    un secret codé en dur dans les sources annulerait la protection HMAC
    pour tous les clients si .env est absent ou mal chargé (fail-closed).
    Lu à l'appel (pas au chargement du module) car load_dotenv() s'exécute
    après l'import de ce module dans gui.py."""
    secret = os.getenv("AMAH_LICENSE_SECRET", "").strip()
    if not secret:
        raise RuntimeError(
            "AMAH_LICENSE_SECRET manquant dans .env -- impossible de generer "
            "ou de valider une licence sans ce secret."
        )
    return secret.encode()


def get_machine_id() -> str:
    """Récupère l'UUID unique de la machine Windows."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-WmiObject Win32_ComputerSystemProduct).UUID"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        uid = r.stdout.strip()
        if uid and len(uid) > 10:
            return uid
        # Fallback : numéro de série du BIOS
        r2 = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-WmiObject Win32_BIOS).SerialNumber"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return r2.stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def generate_license_key(machine_id: str) -> str:
    """Génère une clé de licence pour un machine_id donné."""
    raw = hmac.new(_get_secret(), machine_id.encode(), hashlib.sha256).hexdigest()
    # Format : XXXXX-XXXXX-XXXXX-XXXXX (20 caractères hex)
    key = raw[:20].upper()
    return f"{key[:5]}-{key[5:10]}-{key[10:15]}-{key[15:20]}"


def validate_license(key: str) -> bool:
    """Valide une clé de licence sur cette machine."""
    machine_id = get_machine_id()
    if machine_id == "UNKNOWN":
        return False  # Fail closed : refuse si l'ID machine est illisible
    try:
        expected = generate_license_key(machine_id)
    except RuntimeError:
        return False  # Fail closed : pas de secret configure => aucune cle valide
    clean_key = key.upper().replace("-", "").replace(" ", "")
    clean_exp = expected.upper().replace("-", "")
    return clean_key == clean_exp


def is_licensed() -> bool:
    """Vérifie si cette installation est licensée (lit la clé dans .env)."""
    key = os.getenv("AMAH_LICENSE_KEY", "").strip()
    if not key:
        return False
    return validate_license(key)


def get_license_info() -> dict:
    """Retourne les infos de licence."""
    machine_id = get_machine_id()
    key        = os.getenv("AMAH_LICENSE_KEY", "")
    valid      = validate_license(key) if key else False
    return {
        "success":    True,
        "machine_id": machine_id,
        "active":     valid,
        "cle":        key[:5] + "..." if key else "Aucune",
    }


# ── Outil en ligne de commande pour générer une clé ─────────────────────────
if __name__ == "__main__":
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    if len(sys.argv) == 2:
        mid = sys.argv[1]
        key = generate_license_key(mid)
        print(f"Machine ID : {mid}")
        print(f"Cle        : {key}")
    else:
        mid = get_machine_id()
        key = generate_license_key(mid)
        print(f"Machine ID de ce PC : {mid}")
        print(f"Cle generee         : {key}")
        print()
        print("Pour generer une cle pour un client :")
        print("  py -3.13 tools/license.py <machine_id_client>")
