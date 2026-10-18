"""Vérifie les licences signées (tools/license.py) — sans appel API.

Lancer depuis la racine du projet :
    py -3.13 -m benchmarks.benchmark_license

Utilise une paire de clés jetable pour les signatures ; vérifie aussi que la
clé privée du .env développeur (si présente) correspond à la clé publique
embarquée dans le code. Code de sortie 1 si une vérification échoue.
"""
import base64
import os
import sys

from dotenv import dotenv_values

import tools.license as L

results = []


def check(label, condition):
    results.append(bool(condition))
    print(("OK    " if condition else "ECHEC ") + label)


private_b64, public_b64 = L.generate_keypair()
machine = "4C4C4544-0042-3510-8051-B4C04F5A4E32"
key = L.sign_machine_id(machine, private_b64)

check("clé valide pour sa machine", L.verify_license(machine, key, public_b64))
check("clé refusée sur une autre machine",
      not L.verify_license("4C4C4544-0042-3510-8051-B4C04F5A4E33", key, public_b64))
check("insensible à la casse, aux espaces et aux tirets",
      L.verify_license(machine.lower(), key.lower().replace("-", " "), public_b64))
tampered = ("B" if key[0] != "B" else "C") + key[1:]
check("clé modifiée d'un caractère refusée", not L.verify_license(machine, tampered, public_b64))
check("ancien format HMAC refusé", not L.verify_license(machine, "ABCDE-12345-FGHIJ-67890", public_b64))
check("texte quelconque refusé", not L.verify_license(machine, "n'importe quoi", public_b64))
other_private, _ = L.generate_keypair()
check("clé signée par une autre clé privée refusée",
      not L.verify_license(machine, L.sign_machine_id(machine, other_private), public_b64))

saved = os.environ.pop("AMAH_LICENSE_PRIVATE_KEY", None)
try:
    L.generate_license_key(machine)
    check("génération impossible sans clé privée", False)
except RuntimeError:
    check("génération impossible sans clé privée", True)
finally:
    if saved is not None:
        os.environ["AMAH_LICENSE_PRIVATE_KEY"] = saved

check("aucune clé privée dans le code source",
      "AMAH_LICENSE_PRIVATE_KEY=" not in open(L.__file__, encoding="utf-8").read().split("if __name__")[0])

dev_private = (dotenv_values(".env").get("AMAH_LICENSE_PRIVATE_KEY") or "").strip() if os.path.exists(".env") else ""
if dev_private:
    from cryptography.hazmat.primitives import serialization as s
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    derived = base64.b64encode(Ed25519PrivateKey.from_private_bytes(base64.b64decode(dev_private))
                               .public_key().public_bytes(s.Encoding.Raw, s.PublicFormat.Raw)).decode()
    check("clé privée du .env = clé publique du code", derived == L.PUBLIC_KEY_B64)
    real_key = L.sign_machine_id(machine, dev_private)
    check("licence signée avec la vraie clé acceptée par le code", L.verify_license(machine, real_key))
else:
    print("(pas de clé privée dans .env : vérifications de la vraie paire ignorées)")

print(f"\n{sum(results)}/{len(results)} vérifications réussies")
sys.exit(0 if all(results) else 1)
