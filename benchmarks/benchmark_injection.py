"""Vérifie qu'aucun texte venu de l'extérieur (sujet d'email, page web lue,
texte copié) n'est inséré dans le code d'un script PowerShell — sans lancer
PowerShell, sans son, sans appel API.

Lancer depuis la racine du projet :
    py -3.13 -m benchmarks.benchmark_injection

Contexte (18/10/2026) : PowerShell traite aussi ’ ‘ comme des apostrophes et
“ ” „ comme des guillemets, "\\"" n'y échappe rien et "$(...)" s'exécute dans
une chaîne entre guillemets. Un sujet d'email "Facture’; <commande>; ‘"
exécutait du code via send_notification ; idem pour le repli vocal de speak
et pour write_clipboard. Le texte passe désormais par des variables
d'environnement.
Code de sortie 1 si une vérification échoue.
"""
import subprocess
import sys
import threading

import tools.clipboard as C
import tools.notifications as N
import tools.voice as V

results = []
PAYLOADS = [
    "Facture’; New-Item amah_temoin.txt; ‘",
    "Bonjour ”); New-Item amah_temoin.txt; (“",
    'x"; New-Item amah_temoin.txt; "',
    "$(New-Item amah_temoin.txt)",
]


def check(label, condition):
    results.append(bool(condition))
    print(("OK    " if condition else "ECHEC ") + label)


class _Done:
    returncode = 0
    stdout = b""
    stderr = b""

    def wait(self):
        return 0

    def poll(self):
        return 0


calls = []


def _fake(args, **kwargs):
    calls.append((args, kwargs.get("env") or {}))
    return _Done()


real_run, real_popen = subprocess.run, subprocess.Popen
subprocess.run = _fake
subprocess.Popen = _fake
try:
    for i, payload in enumerate(PAYLOADS, 1):
        # Notification (lancée dans un fil)
        calls.clear()
        N.send_notification("Email important", payload, duration=1)
        for t in threading.enumerate():
            if t is not threading.current_thread() and t.daemon:
                t.join(timeout=2)
        args, env = calls[-1]
        check(f"notification {i} : texte hors du script, transmis par variable",
              payload not in " ".join(args) and env.get("AMAH_NOTIF_TEXT") == payload)

        # Repli vocal Windows (edge-tts simulé en panne) : la voix Windows est
        # appelée directement (SAPI), plus par PowerShell — aucun shell lancé
        calls.clear()
        saved, saved_sapi = V._run_async_safely, V._sapi_speak
        said = []

        def _panne(factory):
            raise RuntimeError("edge-tts en panne (simulé)")
        V._run_async_safely = _panne
        V._sapi_speak = lambda text, level=2: said.append(text)   # sans son
        try:
            V.speak(payload)
        finally:
            V._run_async_safely, V._sapi_speak = saved, saved_sapi
        check(f"voix (repli) {i} : aucun shell lancé, texte remis tel quel à la voix Windows",
              not calls and said and "New-Item" in said[0])

        # Presse-papiers
        calls.clear()
        C.write_clipboard(payload)
        args, env = calls[-1]
        check(f"presse-papiers {i} : texte hors du script, transmis par variable",
              payload not in " ".join(args) and env.get("AMAH_CLIP_TEXT") == payload)

    calls.clear()
    N.send_notification("t", "m", duration="1; New-Item amah_temoin.txt")
    for t in threading.enumerate():
        if t is not threading.current_thread() and t.daemon:
            t.join(timeout=2)
    args, env = calls[-1]
    check("notification : durée non numérique ramenée à un nombre",
          "New-Item" not in " ".join(args) and env.get("AMAH_NOTIF_MS", "").isdigit())
finally:
    subprocess.run, subprocess.Popen = real_run, real_popen

print(f"\n{sum(results)}/{len(results)} vérifications réussies")
sys.exit(0 if all(results) else 1)
