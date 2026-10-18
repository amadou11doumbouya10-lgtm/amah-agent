"""Vérifie les initiatives d'Amah (tools/email_watch.py, tools/briefing.py,
tools/instant.py) — sans réseau, sans Gmail, sans appel API.

Lancer depuis la racine du projet :
    py -3.13 -m benchmarks.benchmark_initiatives

Code de sortie 1 si une vérification échoue.
"""
import email
import os
import sys
import tempfile
from pathlib import Path

import tools.briefing as B
import tools.email_watch as W
from config import TOOLS_DEFINITIONS
from tools.instant import _BRIEFING
from tools.tool_router import normalize, select_tools

results = []


def check(label, condition):
    results.append(bool(condition))
    print(("OK    " if condition else "ECHEC ") + label)


def hdr(sender, subject="Sujet", **extra):
    lines = [f"From: {sender}", f"Subject: {subject}", "Date: Sun, 18 Oct 2026 09:00:00 +0000"]
    lines += [f"{k.replace('_', '-')}: {v}" for k, v in extra.items()]
    return email.message_from_string("\n".join(lines) + "\n\n")


IMPORTANT = '"\\\\Important" "\\\\Inbox"'
INBOX = '"\\\\Inbox"'

# 1. Classement des emails
c = W.classify(1, IMPORTANT, hdr("Fatou Diallo <fatou@exemple.com>"), set())
check("email personnel marqué Important par Gmail -> important", c["important"] and c["de"] == "Fatou Diallo")
check("email personnel non marqué par Gmail -> pas important",
      not W.classify(2, INBOX, hdr("Fatou <fatou@exemple.com>"), set())["important"])
check("newsletter (List-Unsubscribe) -> pas important, même marquée Important",
      not W.classify(3, IMPORTANT, hdr("Promo <promo@shop.com>", List_Unsubscribe="<mailto:x>"), set())["important"])
check("expéditeur noreply -> envoi automatique",
      W.classify(4, IMPORTANT, hdr("Service <no-reply@banque.com>"), set())["raison"] == "envoi automatique")
check("expéditeur prioritaire (domaine) -> important même en envoi de masse",
      W.classify(5, INBOX, hdr("RH <rh@entreprise.gn>", List_Unsubscribe="<x>"), {"entreprise.gn"})["important"])
check("serveur non Gmail (pas de libellés) : email personnel -> important",
      W.classify(6, None, hdr("Ami <ami@orange.fr>"), set())["important"])
check("sujet encodé (=?UTF-8?) décodé",
      W.classify(7, IMPORTANT, hdr("A <a@b.c>", "=?UTF-8?B?UsOpdW5pb24gbHVuZGk=?="), set())["sujet"] == "Réunion lundi")

# 2. Lecture de la réponse IMAP (FETCH avec libellés Gmail)
raw = [(b'1 (X-GM-LABELS ("\\\\Important" "\\\\Inbox") UID 42 BODY[HEADER.FIELDS (FROM)] {30}',
        b"From: Fatou <fatou@exemple.com>\r\n\r\n"), b")"]
parsed = W._parse_fetch(raw)
check("réponse FETCH lue : UID et libellé Important", parsed and parsed[0][0] == 42 and "\\Important" in parsed[0][1])

# 3. Surveillance : seuls les NOUVEAUX emails importants déclenchent une alerte
inbox = [{"uid": 1, "de": "A", "sujet": "déjà là"}]
W.important_unread = lambda days=2: list(inbox)
watcher = W.EmailWatcher(on_new=lambda m: None, minutes=10)
check("1re vérification : rien (les emails déjà là vont dans le briefing)", watcher.check_once() == [])
inbox.append({"uid": 2, "de": "B", "sujet": "nouveau"})
check("nouvel email important -> une alerte", [m["uid"] for m in watcher.check_once()] == [2])
check("même email au tour suivant -> pas de 2e alerte", watcher.check_once() == [])

# 4. Briefing : composition, source en panne sautée
B._weather_line = lambda: "Météo à Conakry : ensoleillé, 28°C."
B._emails_line = lambda: (_ for _ in ()).throw(OSError("réseau coupé"))
B._tasks_line = lambda: ""
r = B.morning_briefing()
check("briefing : date + météo, source en panne sautée sans erreur",
      "Nous sommes" in r["texte"] and "Conakry" in r["texte"] and r["indisponible"] == ["emails"])

# 5. Une fois par jour
with tempfile.TemporaryDirectory() as tmp:
    B._STATE = Path(tmp) / "amah_state.json"
    saved = os.environ.pop("AMAH_BRIEFING", None)
    hour_ok = __import__("datetime").datetime.now().hour >= 5
    check("pas encore fait aujourd'hui -> briefing dû", B.briefing_due() == hour_ok)
    B.mark_briefing_done()
    check("après le briefing -> plus dû aujourd'hui", not B.briefing_due())
    B._STATE.unlink()
    os.environ["AMAH_BRIEFING"] = "0"
    check("AMAH_BRIEFING=0 -> jamais", not B.briefing_due())
    os.environ.pop("AMAH_BRIEFING")
    if saved is not None:
        os.environ["AMAH_BRIEFING"] = saved

# 6. "Fais-moi le point" sans appel IA, mais pas "le point sur mes dépenses"
yes = ["fais-moi le point", "Amah, fais moi le point stp", "briefing", "le point du jour",
       "qu'est-ce qui est prévu aujourd'hui ?"]
no = ["fais-moi le point sur mes dépenses", "le briefing de la réunion de lundi",
      "quoi de neuf dans l'actualité"]
check("phrases du briefing reconnues", all(_BRIEFING.match(normalize(q)) for q in yes))
check("phrases voisines non interceptées", not any(_BRIEFING.match(normalize(q)) for q in no))
names = [t["function"]["name"] for t in select_tools("fais-moi le point sur la météo et mes emails", TOOLS_DEFINITIONS)[0]]
check("routeur : morning_briefing proposé pour une variante", "morning_briefing" in names)

print(f"\n{sum(results)}/{len(results)} vérifications réussies")
sys.exit(0 if all(results) else 1)
