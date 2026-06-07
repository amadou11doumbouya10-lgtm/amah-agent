import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import parsedate_to_datetime

IMAP_HOST = 'imap.gmail.com'
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587


def _creds():
    address  = os.getenv('GMAIL_ADDRESS', '').strip()
    password = os.getenv('GMAIL_APP_PASSWORD', '').replace(' ', '')
    if not address or not password:
        raise ValueError(
            "GMAIL_ADDRESS ou GMAIL_APP_PASSWORD manquant dans .env\n"
            "Setup (2 min) :\n"
            "1. Active la validation en 2 étapes sur ton compte Google\n"
            "2. Va dans : Compte Google → Sécurité → Mots de passe des applications\n"
            "3. Crée un mot de passe pour 'Autre' → copie le code 16 caractères\n"
            "4. Dans .env, ajoute :\n"
            "   GMAIL_ADDRESS=ton@gmail.com\n"
            "   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx"
        )
    return address, password


def _decode(value: str) -> str:
    parts = decode_header(value or '')
    result = ''
    for part, charset in parts:
        if isinstance(part, bytes):
            result += part.decode(charset or 'utf-8', errors='replace')
        else:
            result += str(part)
    return result


def _extract_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode('utf-8', errors='replace')
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode('utf-8', errors='replace')
    return ''


def read_emails(n: int = 5) -> dict:
    """
    Lit les N derniers emails Gmail triés par DATE réelle.
    Stratégie : récupère les N*4 derniers UIDs, lit leurs en-têtes de date,
    trie par date décroissante, retourne les N plus récents.
    Cela garantit les vrais derniers emails même si les UIDs ne sont pas chronologiques.
    """
    conn = None
    try:
        address, password = _creds()
        conn = imaplib.IMAP4_SSL(IMAP_HOST)
        conn.login(address, password)
        conn.select('INBOX')

        # 1. Emails des 14 derniers jours (pool suffisant, requête rapide)
        from datetime import datetime, timedelta
        since = (datetime.now() - timedelta(days=14)).strftime("%d-%b-%Y")
        _, data = conn.uid('SEARCH', None, f'SINCE {since}')
        all_uids = data[0].split() if data[0] else []

        if not all_uids:
            # Fallback : 60 derniers messages toutes dates
            _, data = conn.uid('SEARCH', None, 'ALL')
            all_uids = (data[0].split() if data[0] else [])[-60:]

        if not all_uids:
            return {'success': True, 'total': 0, 'emails': [], 'message': 'Boite vide'}

        # 2. Prend les N*3 derniers UIDs comme candidats
        pool_size = min(len(all_uids), n * 3)
        candidate_uids = all_uids[-pool_size:]

        # 3. Récupère en-têtes DATE + FROM + SUBJECT + LIST-UNSUBSCRIBE pour chaque candidat
        # LIST-UNSUBSCRIBE est présent dans TOUS les newsletters — absent dans les emails perso
        emails_with_date = []
        for uid in candidate_uids:
            _, hdr_data = conn.uid(
                'FETCH', uid,
                '(BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT LIST-UNSUBSCRIBE)])'
            )
            if not hdr_data or not hdr_data[0] or not isinstance(hdr_data[0], tuple):
                continue
            hdr          = email.message_from_bytes(hdr_data[0][1])
            date_str     = hdr.get('Date', '')
            from_str     = _decode(hdr.get('From', ''))
            subj_str     = _decode(hdr.get('Subject', ''))
            is_newsletter = bool(hdr.get('List-Unsubscribe', ''))
            try:
                dt = parsedate_to_datetime(date_str)
            except Exception:
                dt = None
            emails_with_date.append((uid, dt, date_str, from_str, subj_str, is_newsletter))

        # 4. Trie par date décroissante
        emails_with_date.sort(
            key=lambda x: x[1].timestamp() if x[1] else 0,
            reverse=True
        )

        # 4b. Priorité aux emails personnels (sans List-Unsubscribe = pas un newsletter)
        personal = [e for e in emails_with_date if not e[5]]   # sans List-Unsubscribe
        promo    = [e for e in emails_with_date if e[5]]        # avec List-Unsubscribe
        # Emails perso en premier (déjà triés par date), puis newsletters si pas assez
        ranked = personal + promo
        top_n  = ranked[:n]

        # 5. Télécharge le corps uniquement pour les N sélectionnés
        emails = []
        for uid, dt, date_str, de, sujet, _ in top_n:
            _, msg_data = conn.uid('FETCH', uid, '(RFC822)')
            if not msg_data or not msg_data[0]:
                # Fallback si le corps n'est pas dispo
                emails.append({'de': de, 'sujet': sujet,
                               'date': date_str, 'extrait': '(corps non disponible)'})
                continue
            msg  = email.message_from_bytes(msg_data[0][1])
            body = _extract_body(msg)
            emails.append({
                'de':      _decode(msg.get('From', de)),
                'sujet':   _decode(msg.get('Subject', sujet)),
                'date':    msg.get('Date', date_str),
                'extrait': body[:300].strip(),
            })

        return {'success': True, 'total': len(emails), 'emails': emails}
    except Exception as e:
        return {'error': str(e)}
    finally:
        try:
            if conn:
                conn.logout()
        except Exception:
            pass


def send_email(to: str, subject: str, body: str) -> dict:
    try:
        address, password = _creds()
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['From']    = address
        msg['To']      = to
        msg['Subject'] = subject

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(address, password)
            server.sendmail(address, to, msg.as_string())

        return {'success': True, 'message': f'Email envoyé à {to}'}
    except Exception as e:
        return {'error': str(e)}


def search_emails(query: str) -> dict:
    conn = None
    try:
        address, password = _creds()
        conn = imaplib.IMAP4_SSL(IMAP_HOST)
        conn.login(address, password)
        conn.select('INBOX')

        safe_query = query.replace('"', '\\"')
        _, data = conn.search(None, f'X-GM-RAW "{safe_query}"')
        ids = data[0].split()
        to_fetch = ids[-10:][::-1]

        emails = []
        for uid in to_fetch:
            _, msg_data = conn.fetch(uid, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])
            emails.append({
                'de':    _decode(msg.get('From', '')),
                'sujet': _decode(msg.get('Subject', '')),
                'date':  msg.get('Date', ''),
            })

        return {'success': True, 'requete': query, 'total': len(emails), 'emails': emails}
    except Exception as e:
        return {'error': str(e)}
    finally:
        try:
            if conn:
                conn.logout()
        except Exception:
            pass


def draft_email(to: str, subject: str, body: str) -> dict:
    """Prépare un brouillon d'email sans l'envoyer. Présente le contenu à l'utilisateur pour validation."""
    if not to or not subject or not body:
        return {"error": "Destinataire, sujet et corps sont requis pour le brouillon."}
    return {
        "success":      True,
        "brouillon":    True,
        "destinataire": to,
        "sujet":        subject,
        "corps":        body,
        "message":      f"Brouillon prêt pour {to}. Dis 'envoie' pour confirmer ou 'annule' pour abandonner.",
    }
