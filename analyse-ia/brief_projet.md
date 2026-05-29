# Brief — Projet Amah Agent
*Dernière mise à jour : 29/05/2026 — Version 1.0.0 finale*

## Contexte
Agent IA local sur PC Windows — 65 outils, prêt à la vente commerciale.
Cerveau : Groq API (llama-3.3-70b-versatile, gratuit).
Interfaces : terminal Rich (agent.py) + fenêtre graphique tkinter (gui.py).
Langage : Python 3.13. Packaging : PyInstaller (.exe 114 Mo standalone).
Email officiel : contact.amah.officiel@gmail.com

## Les 65 outils par catégorie

| Catégorie | Outils | Fichier |
|-----------|--------|---------|
| Fichiers/dossiers | 7 | tools/files.py |
| Documents Word/PDF/TXT | 4 | tools/documents.py |
| Recherche web | 2 | tools/search.py |
| Système Windows | 3 | tools/system.py |
| Mémoire SQLite | 3 | tools/memory.py |
| Email Gmail | 3 | tools/email_tool.py |
| Navigateur Chrome | 5 | tools/browser.py |
| Voix (synthèse) | 1 | tools/voice.py |
| Notifications/rappels | 2 | tools/notifications.py |
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
| Statistiques d'usage | 2 | tools/stats.py |
| Mises à jour | 2 | tools/updater.py |
| Licence | 1 | tools/license.py |
| **TOTAL** | **65** | |

## Architecture technique

### Source unique des outils
`tools/__init__.py` contient TOOL_FUNCTIONS — le dict central de tous les 65 outils.
`agent.py` et `gui.py` importent simplement : `from tools import TOOL_FUNCTIONS`
→ Ajouter un outil = modifier 3 fichiers seulement (outil + __init__ + config)

### Mémoire persistante (amah_memory.db)
- `conversations` : historique auto, 40 derniers rechargés au démarrage
- `memories` : mémoire explicite long terme par catégorie
- `tool_usage` : statistiques d'utilisation par outil
- Trimming contexte API : system prompt + 60 derniers messages max

### Système de licence offline
- Clé HMAC-SHA256 liée au Machine UUID Windows
- Génération : `py -3.13 tools/license.py <machine_uuid>`
- Clé secrète dans `tools/license.py` (_SECRET)
- Script rapide : `developpeur/generate_license.bat`

### Mises à jour automatiques
- Version actuelle : 1.0.0 (dans tools/updater.py)
- Mécanisme : vérifie un fichier JSON hébergé publiquement
- À configurer : VERSION_URL dans tools/updater.py

## Interface graphique (gui.py)
- Écran de configuration automatique au premier lancement
- Horodatage [HH:MM] sur chaque message
- Affichage des outils utilisés inline (en italique doré)
- Barre d'état : Prêt / réfléchit... / outil en cours
- Entrée multi-ligne (Shift+Entrée)
- Boutons Copier + Réinitialiser dans le header
- Raccourcis : Ctrl+R, Ctrl+C, Échap
- Menu clic droit sur le chat

## Distribution client
```
dist/
├── Amah Agent.exe              (114 Mo, standalone, 65 outils)
├── .env                        (Gmail pré-configuré, Groq à renseigner)
├── installer_navigateur.bat    (Chrome, une seule fois)
└── Guide_Installation_Client.docx
```

## Dossier développeur
```
developpeur/
├── README_DEVELOPPEUR.md       Vue d'ensemble technique
├── GUIDE_LICENCE.md            Système de licence complet
├── GUIDE_BUILD.md              Compiler le .exe
├── GUIDE_MISE_A_JOUR.md        Publier une mise à jour
├── GUIDE_AJOUT_OUTIL.md        Ajouter un outil (5 étapes)
└── generate_license.bat        Génère une clé client
```

## Dépendances (requirements.txt)
```
groq, python-dotenv, rich, ddgs, python-docx, fpdf2, pypdf, psutil,
playwright, pillow, openpyxl, pyttsx3, deep-translator, qrcode[pil],
SpeechRecognition, pyaudio
```

## Sécurité
- run_command bloque les commandes destructives
- Toutes les clés dans .env (jamais dans le code ni le .exe)
- Licence liée au hardware (non transférable entre PC)
- Trimming contexte pour éviter les fuites de données en mémoire longue

## Ce qui reste à faire (futur)
- Activer la vérification de licence obligatoire au démarrage
- Héberger version.json pour les mises à jour automatiques
- Google Calendar (agenda)
- Mode mains libres (listen + speak en boucle)
- Telegram bot
- Dashboard journalier automatique
