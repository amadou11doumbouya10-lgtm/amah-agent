# Brief — Projet Amah Agent
*Dernière mise à jour : 29/05/2026 — Version 1.0.0 stable*

## Contexte
Agent IA local PC Windows. 65 outils. Prêt à la vente commerciale.
Cerveau : Groq API (llama-3.3-70b-versatile, gratuit).
Interfaces : terminal Rich + fenêtre graphique tkinter.
Python 3.13 · PyInstaller (.exe 114 Mo standalone).
Email officiel : contact.amah.officiel@gmail.com

## Architecture clé
- `tools/__init__.py` — source unique de TOOL_FUNCTIONS (65 outils)
- `gui.py` — interface graphique + SetupWindow + LicenseWindow
- `config.py` — 65 définitions outils + system prompt compact (1 544 chars)
- `amah_memory.db` — SQLite (conversations + memories + tool_usage)

## Les 65 outils (sync config ↔ tools vérifiée = 65 = 65)

| Catégorie | Outils | Fichier |
|-----------|--------|---------|
| Fichiers | 7 | tools/files.py |
| Documents | 4 | tools/documents.py |
| Recherche web | 2 | tools/search.py |
| Système | 3 | tools/system.py |
| Mémoire | 3 | tools/memory.py |
| Email Gmail | 3 | tools/email_tool.py |
| Navigateur | 5 | tools/browser.py |
| Voix | 1 | tools/voice.py |
| Notifications | 2 | tools/notifications.py |
| Excel | 3 | tools/excel.py |
| Presse-papiers | 2 | tools/clipboard.py |
| Calcul/date | 5 | tools/utils.py |
| Archives ZIP | 3 | tools/archive.py |
| Images/réseau | 6 | tools/image_tool.py |
| Météo | 2 | tools/meteo.py |
| Traduction | 2 | tools/translator.py |
| QR Code | 1 | tools/qrcode_tool.py |
| Reconnaissance vocale | 2 | tools/voice_recognition.py |
| Planificateur Windows | 4 | tools/scheduler.py |
| Statistiques | 2 | tools/stats.py |
| Mises à jour | 2 | tools/updater.py |
| Licence | 1 | tools/license.py |

## Sécurité — corrections appliquées

### PowerShell (tools/system.py)
- 14 mots-clés bloqués (rm -rf, invoke-expression, downloadstring, wget, etc.)
- 5 caractères interdits : & && || ` $(
- Validation dans scheduler.py (heure 0-23, minute 0-59, guillemets échappés)

### Email IMAP (tools/email_tool.py)
- `conn = None` + `try/finally conn.logout()` sur read_emails ET search_emails
- Lecture des emails par numéro de séquence IMAP (chronologique garanti)
- Requête de recherche échappée contre injection

### Mémoire (tools/memory.py)
- `except: pass` → `log.warning()` partout
- Context manager `with sqlite3.connect()` pour save_message
- `cleanup_old_messages(90)` appelé au démarrage (purge auto > 90 jours)

### Playwright (tools/browser.py)
- `atexit.register(_close_browser)` — Chrome fermé proprement à la fin

### Licence (tools/license.py)
- Clé secrète lue depuis `.env` (AMAH_LICENSE_SECRET) avec fallback
- Jamais hardcodée dans le code

### Mise à jour (tools/updater.py)
- Détecte si VERSION_URL est encore un placeholder → message clair

## Système de licence
- Offline HMAC-SHA256 lié au Machine UUID Windows
- Clé secrète dans .env (AMAH_LICENSE_SECRET)
- Génération : `py -3.13 tools/license.py <uuid>` ou `developpeur/generate_license.bat`
- **Obligatoire** au démarrage — LicenseWindow si clé absente/invalide
- LicenseWindow affiche le UUID + bouton Copier + champ de saisie
- Clé sauvegardée dans .env après validation

## Interface graphique (gui.py)
Flux de démarrage :
```
.exe lancé → charger .env
    ↓
Pas de GROQ_API_KEY ? → SetupWindow (crée .env)
    ↓
Pas de licence valide ? → LicenseWindow (activation)
    ↓
AmahGUI (chat principal)
```

Améliorations UI :
- Horodatage [HH:MM] sur chaque message
- Outils utilisés affichés APRÈS la réponse (format : `[ recherche web → lecture page ]`)
- Barre d'état dynamique
- Bouton Copier lit directement le dernier message Amah dans le widget (plus fiable)
- Ctrl+C ne remplace plus la sélection de texte manuelle
- Entrée multi-ligne (Shift+Entrée)
- MAX_MESSAGES = 40 (contexte API)
- Nettoyage auto messages > 90 jours au démarrage

## Performances
- System prompt : 1 544 chars (réduit de -40%)
- Contexte max : 40 messages (réduit de 60)
- Historique chargé : 20 messages (réduit de 40)
- Trimming : [system] + 60 derniers avant chaque appel API

## Distribution client
```
dist/
├── Amah Agent.exe          (114 Mo, standalone)
├── .env                    (Gmail pré-configuré, Groq + Licence à renseigner)
├── installer_navigateur.bat
└── Guide_Installation_Client.docx
```

## Dossier développeur
```
developpeur/
├── README_DEVELOPPEUR.md
├── GUIDE_LICENCE.md + GUIDE_LICENCE_COMPLET.docx
├── GUIDE_BUILD.md
├── GUIDE_MISE_A_JOUR.md
├── GUIDE_AJOUT_OUTIL.md
└── generate_license.bat
```

## Dépendances
groq, python-dotenv, rich, ddgs, python-docx, fpdf2, pypdf, psutil,
playwright, pillow, openpyxl, pyttsx3, deep-translator, qrcode[pil],
SpeechRecognition, pyaudio

## Améliorations v1.2 (appliquées)

### Performance
- **Cache LRU 10min** sur web_search et read_webpage — évite requêtes doublons dans la session
- **Retry backoff exponentiel** Groq (1s → 2s → 4s) sur erreurs 429 et 503
- **Trimming contexte corrigé** — préserve les paires tool_call/tool_result orphelines

### Robustesse
- **Playwright check** au démarrage — avertissement si Chrome non installé
- **Rapport de crash auto** — email à contact.amah.officiel@gmail.com sur exception non gérée
- **check_update opérationnel** — version.json hébergé sur GitHub, URL réelle configurée

### Ce que le prompt suggérait et pourquoi on a skip
- Routeur d'intention : ajoute latence + risque de casser des cas limites
- Streaming tkinter : complexe, gain UX modéré, à faire en v2
- Onboarding 5 étapes : nice to have, pas bloquant pour la vente
- Stats tab GUI : nice to have, données disponibles dans get_stats()

## Futur
- Licence entreprise volume (Option B — clé unique pour N postes)
- Google Calendar (agenda)
- Mode mains libres (listen + speak en boucle)
- Dashboard journalier automatique
- Streaming réponse Groq dans tkinter
