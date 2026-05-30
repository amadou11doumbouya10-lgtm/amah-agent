# Brief — Projet Amah Agent
*Dernière mise à jour : 30/05/2026 — Version 1.0.0 stable (v1.2 améliorations)*

## Contexte
Agent IA local PC Windows — 65 outils — prêt à la vente commerciale.
Cerveau : Groq API (llama-3.3-70b-versatile, gratuit).
Interfaces : terminal Rich + fenêtre graphique tkinter.
Python 3.13 · PyInstaller → .exe 114 Mo standalone.
Email officiel : contact.amah.officiel@gmail.com
GitHub : github.com/amadou11doumbouya10-lgtm/amah-agent

---

## Architecture

### Source unique des outils
`tools/__init__.py` — TOOL_FUNCTIONS (65 outils). Sync config ↔ tools vérifiée = **65 = 65**.
Ajouter un outil = 3 fichiers : outil + __init__ + config.

### Flux de démarrage
```
.exe lancé → charger .env
    ↓
Pas de GROQ_API_KEY ? → SetupWindow (crée .env automatiquement)
    ↓
Playwright non installé ? → Avertissement non bloquant
    ↓
Pas de licence valide ? → LicenseWindow (UUID affiché + champ clé)
    ↓
AmahGUI (chat principal)
```

### Mémoire persistante (amah_memory.db SQLite)
- `conversations` : historique auto, 20 derniers rechargés au démarrage
- `memories` : mémoire explicite long terme par catégorie
- `tool_usage` : statistiques d'utilisation
- Cleanup auto des messages > 90 jours au démarrage
- Trimming API : [system] + 40 derniers messages max

---

## Les 65 outils

| Catégorie | Nb | Fichier |
|---|---|---|
| Fichiers/dossiers | 7 | tools/files.py |
| Documents Word/PDF/TXT | 4 | tools/documents.py |
| Recherche web (avec cache LRU 10min) | 2 | tools/search.py |
| Système Windows | 3 | tools/system.py |
| Mémoire SQLite | 3 | tools/memory.py |
| Email Gmail SMTP/IMAP | 3 | tools/email_tool.py |
| Navigateur Chrome Playwright | 5 | tools/browser.py |
| Synthèse vocale Windows | 1 | tools/voice.py |
| Notifications + rappels | 2 | tools/notifications.py |
| Excel | 3 | tools/excel.py |
| Presse-papiers | 2 | tools/clipboard.py |
| Calcul / date / password / conversion | 5 | tools/utils.py |
| Archives ZIP | 3 | tools/archive.py |
| Images + réseau + processus | 6 | tools/image_tool.py |
| Météo wttr.in | 2 | tools/meteo.py |
| Traduction deep-translator | 2 | tools/translator.py |
| QR Code | 1 | tools/qrcode_tool.py |
| Reconnaissance vocale | 2 | tools/voice_recognition.py |
| Planificateur Windows Task Scheduler | 4 | tools/scheduler.py |
| Statistiques d'usage | 2 | tools/stats.py |
| Mises à jour automatiques | 2 | tools/updater.py |
| Licence offline | 1 | tools/license.py |

---

## Sécurité

### PowerShell (tools/system.py + scheduler.py)
- 14 mots-clés bloqués (rm -rf, invoke-expression, downloadstring, wget, Remove-Item -Recurse...)
- 5 caractères interdits : `&` `&&` `||` `` ` `` `$(`
- scheduler.py : validation heure (0-23), minute (0-59), guillemets échappés

### Email IMAP (tools/email_tool.py)
- `conn = None` + `try/finally conn.logout()` sur read_emails ET search_emails
- Lecture par numéro de séquence IMAP (chronologique garanti)
- Requête de recherche échappée

### Mémoire (tools/memory.py)
- `log.warning()` à la place de `except: pass`
- Context manager `with sqlite3.connect()`
- Cleanup auto messages > 90 jours

### Playwright (tools/browser.py)
- `atexit.register(_close_browser)` — Chrome fermé proprement

### Licence (tools/license.py)
- Clé secrète dans `.env` (AMAH_LICENSE_SECRET), jamais hardcodée

### Mise à jour (tools/updater.py)
- VERSION_URL pointe sur le vrai repo GitHub
- version.json hébergé sur GitHub (check_update() opérationnel)

---

## Performance

### Cache LRU (tools/search.py)
- web_search et read_webpage mis en cache 10 minutes
- Même requête deux fois dans la session → résultat instantané
- Limite 50 entrées, éviction LRU automatique

### Retry backoff Groq (gui.py)
- Erreurs 429/503 → retry automatique 1s → 2s → 4s
- Barre d'état affiche "Limite atteinte — attente Xs..."

### Trimming contexte corrigé (gui.py)
- Préserve les paires tool_call/tool_result orphelines
- MAX_MESSAGES = 40
- System prompt compact : 1 544 chars (-40%)

### Rapport de crash (gui.py)
- Exception non gérée → email auto à contact.amah.officiel@gmail.com

---

## Système de licence

### Principe (offline HMAC-SHA256)
- Chaque PC Windows a un Machine UUID unique
- Clé = HMAC-SHA256(UUID, AMAH_LICENSE_SECRET)[:20] formaté en XXXXX-XXXXX-XXXXX-XXXXX
- Clé liée au hardware — non transférable

### Processus vendeur → client
1. Client envoie son Machine UUID (affiché dans LicenseWindow ou via PowerShell)
2. Vendeur génère la clé : `py -3.13 tools/license.py <UUID>` ou `developpeur/generate_license.bat`
3. Vendeur envoie la clé par email
4. Client l'entre dans LicenseWindow → sauvegardée dans .env → Amah démarre

### Gestion des licences
- Tableau Excel : `Tableau_Licences_Amah.xlsx` (bureau du vendeur)
- Colonnes : N° | Date | Nom | Email | UUID | Clé | Version | Prix | Statut | Notes
- Documentation complète : `developpeur/GUIDE_LICENCE_COMPLET.docx`

### Licence entreprise (futur — Option B)
- Clé volume qui fonctionne sur N machines sans UUID spécifique
- Non encore implémenté

---

## Interface graphique (gui.py)

### Améliorations UI
- Horodatage [HH:MM] sur chaque message
- Outils affichés après la réponse : `[ recherche web → lecture page ]`
- Barre d'état : Prêt / réfléchit... / Outil : xxx... / Limite atteinte...
- Bouton Copier lit directement le widget (pas de variable stale)
- Ctrl+C normal (ne remplace plus la sélection)
- Entrée multi-ligne (Shift+Entrée)
- Boutons Copier + Réinitialiser dans le header
- Raccourcis : Ctrl+R reset, Échap vider

---

## Distribution client

### Livrable dist/
```
dist/
├── Amah Agent.exe              (114 Mo, standalone)
├── .env                        (Gmail pré-configuré, Groq + Licence à renseigner)
├── installer_navigateur.bat    (Chrome, une seule fois)
└── Guide_Installation_Client.docx
```

### Mises à jour automatiques
- version.json hébergé sur GitHub (raw URL)
- check_update() retourne version actuelle vs disponible
- download_update() remplace le .exe automatiquement

---

## Dossier développeur
```
developpeur/
├── README_DEVELOPPEUR.md
├── GUIDE_LICENCE.md
├── GUIDE_LICENCE_COMPLET.docx  ← guide complet vendeur ↔ client
├── GUIDE_BUILD.md
├── GUIDE_MISE_A_JOUR.md
├── GUIDE_AJOUT_OUTIL.md
└── generate_license.bat
```

---

## Dépendances (requirements.txt)
```
groq, python-dotenv, rich, ddgs, python-docx, fpdf2, pypdf, psutil,
playwright, pillow, openpyxl, pyttsx3, deep-translator, qrcode[pil],
SpeechRecognition, pyaudio
```

---

## Futur
- Licence entreprise volume (Option B — une clé pour N postes)
- Google Calendar (agenda)
- Mode mains libres (listen + speak en boucle)
- Dashboard journalier automatique
- Streaming réponse Groq dans tkinter
- Telegram bot
