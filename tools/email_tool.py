import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.header import decode_header

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
    conn = None
    try:
        address, password = _creds()
        conn = imaplib.IMAP4_SSL(IMAP_HOST)
        conn.login(address, password)
        _, data = conn.select('INBOX')
        total = int(data[0])  # nombre total de messages

        if total == 0:
            conn.logout()
            return {'success': True, 'total': 0, 'emails': [], 'message': 'Boite vide'}

        # Numéros de séquence IMAP — toujours chronologiques
        start = max(1, total - n + 1)
        sequence = list(range(total, start - 1, -1))  # du plus récent au plus ancien

        emails = []
        for num in sequence:
            _, msg_data = conn.fetch(str(num), '(RFC822)')
            if not msg_data or not msg_data[0]:
                continue
            msg  = email.message_from_bytes(msg_data[0][1])
            body = _extract_body(msg)
            emails.append({
                'de':      _decode(msg.get('From', '')),
                'sujet':   _decode(msg.get('Subject', '')),
                'date':    msg.get('Date', ''),
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
