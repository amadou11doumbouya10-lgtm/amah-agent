"""Emails importants non lus, et surveillance de la boîte — sans appel IA.

Boîte ouverte en lecture seule (EXAMINE) et en-têtes lus avec BODY.PEEK :
aucun email n'est marqué comme lu.

Important = pas un envoi de masse (newsletter, notification automatique) ET
(marqué Important par Gmail OU expéditeur prioritaire). Les expéditeurs
prioritaires (AMAH_VIP_EMAILS, adresses ou domaines séparés par des virgules)
sont toujours importants.
"""
import email
import imaplib
import logging
import os
import re
import threading
from datetime import datetime, timedelta
from email.utils import parseaddr, parsedate_to_datetime

from tools.email_tool import IMAP_HOST, _creds, _decode

log = logging.getLogger("amah.email_watch")

_AUTOMATED_SENDER = re.compile(
    r"no-?reply|ne-?pas-?repondre|donotreply|notifications?@|newsletter|mailer-daemon|"
    r"bounce|postmaster|marketing|promo|news@|info@|alerts?@",
    re.IGNORECASE,
)
_HEADERS = "DATE FROM SUBJECT LIST-UNSUBSCRIBE PRECEDENCE AUTO-SUBMITTED"


def gmail_configured() -> bool:
    try:
        _creds()
        return True
    except ValueError:
        return False


def _vip() -> set:
    raw = os.getenv("AMAH_VIP_EMAILS", "")
    return {v.strip().lower().lstrip("@") for v in re.split(r"[,;\s]+", raw) if v.strip()}


def _is_vip(address: str, vip: set) -> bool:
    address = address.lower()
    return address in vip or address.rsplit("@", 1)[-1] in vip


def _is_automated(hdr, address: str) -> bool:
    if hdr.get("List-Unsubscribe"):
        return True
    if (hdr.get("Precedence") or "").strip().lower() in ("bulk", "list", "junk"):
        return True
    auto = (hdr.get("Auto-Submitted") or "").strip().lower()
    if auto and auto != "no":
        return True
    return bool(_AUTOMATED_SENDER.search(address))


def _parse_fetch(data) -> list:
    """Réponse FETCH -> [(uid, labels_gmail ou None, en-têtes)]."""
    items = []
    for part in data or []:
        if not isinstance(part, tuple) or len(part) < 2:
            continue
        meta = part[0].decode(errors="replace") if isinstance(part[0], bytes) else str(part[0])
        uid = re.search(r"UID (\d+)", meta)
        labels = re.search(r"X-GM-LABELS \((.*?)\)", meta)
        if uid:
            items.append((int(uid.group(1)), labels.group(1) if labels else None,
                          email.message_from_bytes(part[1])))
    return items


def unread_emails(days: int = 3, limit: int = 40) -> list:
    """Emails non lus des `days` derniers jours, plus récents d'abord, classés."""
    address, password = _creds()
    conn = imaplib.IMAP4_SSL(IMAP_HOST, timeout=20)
    try:
        conn.login(address, password)
        conn.select("INBOX", readonly=True)
        since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        _, data = conn.uid("SEARCH", None, f"(UNSEEN SINCE {since})")
        uids = (data[0].split() if data and data[0] else [])[-limit:]
        if not uids:
            return []
        uid_set = b",".join(uids).decode()
        try:
            _, data = conn.uid("FETCH", uid_set, f"(X-GM-LABELS BODY.PEEK[HEADER.FIELDS ({_HEADERS})])")
        except imaplib.IMAP4.error:
            # Serveur non Gmail : pas de libellé "Important"
            _, data = conn.uid("FETCH", uid_set, f"(BODY.PEEK[HEADER.FIELDS ({_HEADERS})])")
    finally:
        try:
            conn.logout()
        except Exception as e:
            log.debug(f"Deconnexion IMAP ignoree : {e}")

    vip = _vip()
    emails = [classify(uid, labels, hdr, vip) for uid, labels, hdr in _parse_fetch(data)]
    emails.sort(key=lambda e: e["date"].timestamp() if e["date"] else 0, reverse=True)
    return emails


def classify(uid: int, labels, hdr, vip: set) -> dict:
    """Un email (en-têtes + libellés Gmail, None hors Gmail) -> dict classé."""
    name, addr = parseaddr(_decode(hdr.get("From", "")))
    try:
        date = parsedate_to_datetime(hdr.get("Date", ""))
    except Exception:
        date = None
    is_vip = _is_vip(addr, vip)
    automated = _is_automated(hdr, addr)
    gmail_important = labels is not None and "\\Important" in labels
    # Sans libellés Gmail (autre serveur), un email personnel compte comme important
    important = is_vip or (not automated and (gmail_important or labels is None))
    return {
        "uid": uid,
        "de": name or addr,
        "adresse": addr,
        "sujet": _decode(hdr.get("Subject", "")).strip() or "(sans sujet)",
        "date": date,
        "important": important,
        "raison": "expéditeur prioritaire" if is_vip else (
            "envoi automatique" if automated else (
                "marqué Important par Gmail" if gmail_important else "personnel")),
    }


def important_unread(days: int = 3) -> list:
    return [e for e in unread_emails(days) if e["important"]]


class EmailWatcher:
    """Vérifie la boîte toutes les `minutes` et appelle on_new(email) pour
    chaque NOUVEL email important (ceux déjà là au démarrage ne déclenchent
    rien : le briefing du jour les annonce)."""

    def __init__(self, on_new, minutes: float = None):
        if minutes is None:
            try:
                minutes = float(os.getenv("AMAH_EMAIL_CHECK_MINUTES", "10"))
            except ValueError:
                minutes = 10
        self.on_new = on_new
        self.interval = max(2.0, minutes) * 60
        self._stop = threading.Event()
        self._seen = None
        self._thread = None

    def check_once(self) -> list:
        """Nouveaux emails importants depuis la dernière vérification."""
        current = important_unread(days=2)
        if self._seen is None:
            self._seen = {e["uid"] for e in current}
            return []
        new = [e for e in current if e["uid"] not in self._seen]
        self._seen |= {e["uid"] for e in current}
        return new

    def _loop(self):
        while not self._stop.is_set():
            try:
                for mail in reversed(self.check_once()):      # plus ancien d'abord
                    self.on_new(mail)
            except Exception as e:
                # Réseau coupé, mot de passe changé... : on réessaie au tour suivant
                log.debug(f"Verification des emails ignoree : {e}")
            self._stop.wait(self.interval)

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="amah-emails", daemon=True)
            self._thread.start()
        return self

    def stop(self):
        self._stop.set()
