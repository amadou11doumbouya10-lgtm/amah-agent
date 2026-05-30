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

# Clé secrète lue depuis .env (AMAH_LICENSE_SECRET) ; fallback sur valeur par défaut
_SECRET = os.getenv("AMAH_LICENSE_SECRET", "amah-agent-2026-mk-secret-key-v1").encode()


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
    raw = hmac.new(_SECRET, machine_id.encode(), hashlib.sha256).hexdigest()
    # Format : XXXXX-XXXXX-XXXXX-XXXXX (20 caractères hex)
    key = raw[:20].upper()
    return f"{key[:5]}-{key[5:10]}-{key[10:15]}-{key[15:20]}"


def validate_license(key: str) -> bool:
    """Valide une clé de licence sur cette machine."""
    machine_id = get_machine_id()
    if machine_id == "UNKNOWN":
        return False  # Fail closed : refuse si l'ID machine est illisible
    expected = generate_license_key(machine_id)
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
