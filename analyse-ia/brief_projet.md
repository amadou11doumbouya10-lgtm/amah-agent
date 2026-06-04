# Brief — Projet Amah Agent
*Dernière mise à jour : 04/06/2026 — Version 1.3.0*

## Contexte
Agent IA local sur PC Windows — 65 outils — version commerciale prête.
Cerveau : Groq API avec routage de modèle automatique.
Interfaces : terminal Rich + fenêtre graphique tkinter.
Python 3.13 · PyInstaller → .exe 125 Mo standalone.
Email officiel : contact.amah.officiel@gmail.com
GitHub : github.com/amadou11doumbouya10-lgtm/amah-agent
Portfolio : amadou11doumbouya10-lgtm.github.io/-theamah-streaming/portfolio.html

---

## Nouveautés v1.3.0

### Routage de modèle automatique
- Questions simples (≤6 mots, salutation) → `llama-3.1-8b-instant` (~0.3s)
- Tâches avec outils → `llama-3.3-70b-versatile` (~2s)
- Impact commercial : réponses instantanées visible en démo

### Logo hexagone officiel
- SVG → PNG 680x680 via Playwright → ICO 7 tailles (16 à 256px)
- Recadré sur l'hexagone seul (sans le texte) pour les petites tailles
- Appliqué sur le .exe et le raccourci bureau

### Email optimisé
- Tri par date UTC réelle (pas par UID IMAP)
- Priorité aux emails personnels (sans header List-Unsubscribe)
- Pool de recherche : 14 derniers jours → sort → top N

### Démarrage instantané
- Check Playwright : vérification fichier `chrome.exe` (3ms vs 30 000ms avant)

### Tokens -75%
- Routeur 90+ mots-clés → 8-12 outils ciblés par appel
- Extensions de fichiers ajoutées : html, py, json, css, js...
- DEFAULT_TOOLS inclut désormais read_emails et speak
- Tokens/appel : ~1 500 vs ~13 000 avant

### Interface v1.3
- Version visible sur : SetupWindow, LicenseWindow, header chat
- SetupWindow : 3 champs Groq + licence + Gmail (tout en un écran)
- Bannière info : "3 clés = 3x plus d'appels/jour (gratuit)"

---

## Architecture

### Routage outils (gui.py → _WORD_TO_CAT)
90+ mots-clés mappés vers 10 catégories :
`fichiers | documents | internet | email | memoire | systeme | utils | data | media | images | info | planif`

### Routage modèle (gui.py → _chat())
```python
if is_simple:   model = "llama-3.1-8b-instant"
else:           model = "llama-3.3-70b-versatile"  # MODEL dans config.py
```

### Rotation clés API
- GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3 dans .env
- Bascule automatique sur 429 → clé suivante
- 3 clés = 300 000 tokens/jour = 200 appels/jour

### Cache LRU recherche web (tools/search.py)
- web_search et read_webpage mis en cache 10 minutes
- Même requête dans la session → résultat instantané

---

## Les 65 outils (source unique : tools/__init__.py)

| Catégorie | Nb | Fichier |
|---|---|---|
| Fichiers/dossiers | 7 | tools/files.py |
| Documents Word/PDF/TXT | 4 | tools/documents.py |
| Recherche web (cache LRU) | 2 | tools/search.py |
| Système Windows | 3 | tools/system.py |
| Mémoire SQLite | 3 | tools/memory.py |
| Email Gmail SMTP/IMAP | 3 | tools/email_tool.py |
| Navigateur Chrome | 5 | tools/browser.py |
| Synthèse vocale | 1 | tools/voice.py |
| Notifications + rappels | 2 | tools/notifications.py |
| Excel | 3 | tools/excel.py |
| Presse-papiers | 2 | tools/clipboard.py |
| Calcul/date/password | 5 | tools/utils.py |
| Archives ZIP | 3 | tools/archive.py |
| Images/réseau/processus | 6 | tools/image_tool.py |
| Météo | 2 | tools/meteo.py |
| Traduction | 2 | tools/translator.py |
| QR Code | 1 | tools/qrcode_tool.py |
| Reconnaissance vocale | 2 | tools/voice_recognition.py |
| Planificateur Windows | 4 | tools/scheduler.py |
| Statistiques | 2 | tools/stats.py |
| Mises à jour auto | 2 | tools/updater.py |
| Licence offline | 1 | tools/license.py |

---

## Sécurité (corrections v1.2-v1.3)
- PowerShell : 14 mots-clés bloqués + 5 caractères interdits (`& && || backtick $(`)
- Email IMAP : try/finally conn.logout(), requête search échappée
- Memory : log.warning() + context manager + cleanup 90 jours auto
- Playwright : atexit fermeture Chrome
- Licence : clé secrète dans .env (AMAH_LICENSE_SECRET)
- Tool results : tronqués 2000 chars mémoire vive, 800 chars DB
- Rapport crash auto : email contact.amah.officiel@gmail.com

---

## Distribution client (v1.3.0)
```
dist/  ←  Kit complet prêt à livrer
├── Amah Agent.exe          (125 Mo, v1.3.0, logo hexagone)
├── .env                    (Gmail configuré, Groq + Licence à renseigner)
├── installer_navigateur.bat (Chrome, une seule fois)
└── GUIDE_INSTALLATION.md
```

**Processus licence :**
1. Client reçoit le .exe → double-clic
2. SetupWindow : entre ses clés Groq + sa clé de licence + Gmail
3. UUID machine affiché + bouton Copier → il te l'envoie
4. Tu génères la clé avec `developpeur/generate_license.bat`
5. Il entre la clé → Amah démarre définitivement

---

## Vidéos de présentation (dossier voix/)
- 6 vidéos finales avec musique + texte
- 3 vidéos avec logo hexagone (amah_v4_logo.mp4, concept3_v4_logo.mp4, concept4_v4_logo.mp4)
- Formats : 16:9 (YouTube/LinkedIn) + 9:16 (TikTok/Reels)
- Voix : Eric ElevenLabs, français, eleven_multilingual_v2

---

## Présence en ligne
| Plateforme | URL | Contenu |
|---|---|---|
| GitHub Amah Agent | github.com/amadou11doumbouya10-lgtm/amah-agent | Code source + README |
| Profil GitHub | github.com/amadou11doumbouya10-lgtm | README profil avec badges |
| Portfolio | amadou11doumbouya10-lgtm.github.io/-theamah-streaming/portfolio.html | 6 projets, parcours complet |

---

## Futur
- Licence entreprise volume (Option B)
- Google Calendar
- Mode mains libres
- Streaming Groq dans tkinter
- Dashboard journalier automatique
- Telegram bot
