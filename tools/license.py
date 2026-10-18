"""
Système de licence offline pour Amah Agent — licences signées (Ed25519).

Une licence est la signature de l'identifiant de la machine Windows (UUID) par
la clé PRIVÉE de l'éditeur, qui ne quitte jamais le .env du développeur
(AMAH_LICENSE_PRIVATE_KEY). Amah ne contient que la clé PUBLIQUE : elle permet
de vérifier une licence, pas d'en fabriquer. Le code peut donc être public.

Avant le 18/10/2026, les licences étaient un HMAC avec un secret partagé : pour
vérifier, chaque client aurait dû avoir ce secret (et donc pouvoir générer des
licences), et il figurait en clair dans l'historique public du dépôt. Les
anciennes clés XXXXX-XXXXX-XXXXX-XXXXX ne sont plus acceptées.

Générer une clé client  : py -3.13 tools/license.py <machine_id>
Clé pour ce PC          : py -3.13 tools/license.py
Nouvelle paire de clés  : py -3.13 tools/license.py --nouvelle-paire
"""
import base64
import os
import subprocess
import sys
import threading

# Clé publique de l'éditeur (Ed25519, 32 octets en base64) — publique par nature.
# Elle correspond à AMAH_LICENSE_PRIVATE_KEY du .env développeur.
PUBLIC_KEY_B64 = "HkS74mc4+32amhzjMF+bXc0zMZwpbrTmmJ8waw9yzpM="


def _run_ps(cmd: str, timeout: int = 10) -> str:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True, text=True, timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return r.stdout.strip()


_machine_id = None
_machine_id_lock = threading.Lock()


def prefetch_machine_id():
    """Lance le calcul de l'identifiant machine (PowerShell, ~0,5 s) en
    arrière-plan : gui.py l'appelle avant ses imports, la vérification de la
    licence trouve ensuite la valeur prête."""
    threading.Thread(target=get_machine_id, name="amah-machine-id", daemon=True).start()


def get_machine_id() -> str:
    """UUID de la machine, calculé une seule fois (verrou : un appel pendant
    le préchargement attend son résultat au lieu de relancer PowerShell)."""
    global _machine_id
    with _machine_id_lock:
        if _machine_id is None:
            uid = _read_machine_id()
            if uid == "UNKNOWN":
                return uid          # échec passager : on réessaiera au prochain appel
            _machine_id = uid
        return _machine_id


def _read_machine_id() -> str:
    """Récupère l'UUID unique de la machine Windows.
    Get-CimInstance (WinRM) répond plus vite et plus fiablement que
    Get-WmiObject (DCOM legacy) sous charge système ; un retry absorbe
    les échecs ponctuels au lieu de tomber en fail-closed sur "UNKNOWN"
    à la moindre lenteur passagère."""
    for _ in range(2):
        try:
            uid = _run_ps("(Get-CimInstance Win32_ComputerSystemProduct).UUID")
            if uid and len(uid) > 10:
                return uid
        except Exception:
            pass
    try:
        # Fallback : numéro de série du BIOS
        sn = _run_ps("(Get-CimInstance Win32_BIOS).SerialNumber")
        return sn or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def _message(machine_id: str) -> bytes:
    """Ce qui est signé : l'identifiant machine normalisé."""
    return str(machine_id or "").strip().upper().encode()


def _encode_key(signature: bytes) -> str:
    """Signature (64 octets) -> clé lisible en base32, par groupes de 8."""
    raw = base64.b32encode(signature).decode().rstrip("=")
    return "-".join(raw[i:i + 8] for i in range(0, len(raw), 8))


def _decode_key(key: str) -> bytes:
    clean = "".join(ch for ch in str(key or "").upper() if ch.isalnum())
    clean += "=" * (-len(clean) % 8)
    return base64.b32decode(clean)


def sign_machine_id(machine_id: str, private_key_b64: str) -> str:
    """Clé de licence pour machine_id, signée avec la clé privée donnée."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64))
    return _encode_key(private_key.sign(_message(machine_id)))


def verify_license(machine_id: str, key: str, public_key_b64: str = PUBLIC_KEY_B64) -> bool:
    """Vrai si key est une signature valide de machine_id. N'utilise que la clé publique."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        signature = _decode_key(key)
        if len(signature) != 64:
            return False
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        public_key.verify(signature, _message(machine_id))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def generate_license_key(machine_id: str) -> str:
    """Génère une clé de licence (nécessite la clé privée du .env développeur).
    Lue à l'appel car load_dotenv() s'exécute après l'import de ce module."""
    private_key_b64 = os.getenv("AMAH_LICENSE_PRIVATE_KEY", "").strip()
    if not private_key_b64:
        raise RuntimeError(
            "AMAH_LICENSE_PRIVATE_KEY manquant dans .env -- seul l'éditeur peut "
            "générer des licences."
        )
    return sign_machine_id(machine_id, private_key_b64)


def validate_license(key: str) -> bool:
    """Valide une clé de licence sur cette machine."""
    machine_id = get_machine_id()
    if machine_id == "UNKNOWN":
        return False  # Fail closed : refuse si l'ID machine est illisible
    return verify_license(machine_id, key)


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


def generate_keypair():
    """Nouvelle paire (clé privée, clé publique) en base64."""
    from cryptography.hazmat.primitives import serialization as s
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    private_key = Ed25519PrivateKey.generate()
    private_b64 = base64.b64encode(private_key.private_bytes(
        s.Encoding.Raw, s.PrivateFormat.Raw, s.NoEncryption())).decode()
    public_b64 = base64.b64encode(private_key.public_key().public_bytes(
        s.Encoding.Raw, s.PublicFormat.Raw)).decode()
    return private_b64, public_b64


# ── Outil en ligne de commande ──────────────────────────────────────────────
if __name__ == "__main__":
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    if len(sys.argv) == 2 and sys.argv[1] == "--nouvelle-paire":
        private_b64, public_b64 = generate_keypair()
        print("Nouvelle paire de cles (les licences deja emises deviendront invalides) :")
        print(f"  .env        : AMAH_LICENSE_PRIVATE_KEY={private_b64}")
        print(f"  license.py  : PUBLIC_KEY_B64 = \"{public_b64}\"")
        print("Ne publie JAMAIS la cle privee.")
    elif len(sys.argv) == 2:
        mid = sys.argv[1]
        print(f"Machine ID : {mid}")
        print(f"Cle        : {generate_license_key(mid)}")
    else:
        mid = get_machine_id()
        print(f"Machine ID de ce PC : {mid}")
        print(f"Cle generee         : {generate_license_key(mid)}")
        print()
        print("Pour generer une cle pour un client :")
        print("  py -3.13 tools/license.py <machine_id_client>")
