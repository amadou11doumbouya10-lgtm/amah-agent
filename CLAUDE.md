# Amah Agent Local

## Présentation
Agent IA local sur PC Windows. Cerveau : Groq (Llama 3.3, gratuit). 65 outils réels.
Projet séparé du chatbot web (avatar Amah). Usage : privé + commercial.
Email officiel Amah : contact.amah.officiel@gmail.com

## Structure
```
amah-agent/
├── agent.py                  ← Interface terminal (Rich, couleurs or/sombre)
├── gui.py                    ← Interface graphique tkinter (écran config + chat)
├── config.py                 ← Modèle, système prompt, 65 définitions outils
├── create_shortcut.py        ← Crée le raccourci .lnk sur le bureau
├── amah_memory.db            ← Base SQLite mémoire persistante (auto-créée)
├── amah.spec                 ← Spec PyInstaller pour le packaging .exe
├── build.bat                 ← Lance la compilation .exe en une commande
├── installer_navigateur.bat  ← Installe Chromium pour les clients (1 seule fois)
├── GUIDE_INSTALLATION.md     ← Guide complet pour les clients
├── Guide_Installation_Client.docx ← Guide Word professionnel pour clients
├── Amah_Agent_Documentation.docx  ← Documentation complète du projet
├── generate_icon.py          ← Génère l'icône .ico (vectoriel Pillow)
├── amah.ico                  ← Icône officielle (A doré, cadre doré)
├── tools/
│   ├── __init__.py           ← SOURCE UNIQUE de TOOL_FUNCTIONS (65 outils)
│   ├── files.py              ← Gestion fichiers/dossiers (7 outils)
│   ├── documents.py          ← Création Word/PDF/TXT, lecture (4 outils)
│   ├── search.py             ← Recherche DuckDuckGo + lecture page web (2 outils)
│   ├── system.py             ← Infos système, ouvrir fichiers, PowerShell (3 outils)
│   ├── memory.py             ← Mémoire SQLite persistante (3 outils)
│   ├── email_tool.py         ← Email Gmail SMTP/IMAP (3 outils)
│   ├── browser.py            ← Navigation web Playwright (5 outils)
│   ├── voice.py              ← Synthèse vocale Windows (1 outil)
│   ├── notifications.py      ← Notifications + rappels (2 outils)
│   ├── excel.py              ← Lecture/création Excel (3 outils)
│   ├── clipboard.py          ← Presse-papiers (2 outils)
│   ├── utils.py              ← Calcul, date, password, conversion (5 outils)
│   ├── archive.py            ← Archives ZIP (3 outils)
│   ├── image_tool.py         ← Images + réseau + processus (6 outils)
│   ├── meteo.py              ← Météo wttr.in (2 outils)
│   ├── translator.py         ← Traduction deep-translator (2 outils)
│   ├── qrcode_tool.py        ← Génération QR codes (1 outil)
│   ├── voice_recognition.py  ← Reconnaissance vocale (2 outils)
│   ├── scheduler.py          ← Planificateur Windows (4 outils)
│   ├── stats.py              ← Statistiques d'usage (2 outils)
│   ├── updater.py            ← Mises à jour automatiques (2 outils)
│   └── license.py            ← Système de licence offline (1 outil)
├── developpeur/              ← Documentation technique interne
│   ├── README_DEVELOPPEUR.md
│   ├── GUIDE_LICENCE.md
│   ├── GUIDE_BUILD.md
│   ├── GUIDE_MISE_A_JOUR.md
│   ├── GUIDE_AJOUT_OUTIL.md
│   └── generate_license.bat
├── idees/                    ← Notes et idées du projet
├── analyse-ia/               ← Briefs pour analyse externe par d'autres IA
├── dist/                     ← Dossier de distribution (généré par build.bat)
│   ├── Amah Agent.exe        (114 Mo, standalone, 65 outils)
│   ├── .env                  (Gmail pré-configuré, Groq à renseigner)
│   ├── installer_navigateur.bat
│   └── Guide_Installation_Client.docx
├── .env                      ← Clé API Groq + Gmail (NE PAS partager)
├── .env.example              ← Modèle à copier
└── requirements.txt          ← Dépendances Python
```

## Installation et lancement
```bash
cd "Desktop/Projets/amah-agent"
pip install -r requirements.txt
py -3.13 -m playwright install chromium   # une seule fois
copy .env.example .env                    # puis éditer .env avec les vraies clés
py -3.13 gui.py                           # interface graphique (recommandé)
py -3.13 agent.py                         # interface terminal
py -3.13 create_shortcut.py              # créer le raccourci bureau (une seule fois)
build.bat                                 # compiler le .exe pour distribution
```

## Clés requises
### Groq (obligatoire)
- Gratuit sur https://console.groq.com
- 30 requêtes/minute, 14 400/jour
- Format : gsk_...

### Gmail (optionnel)
- Compte : contact.amah.officiel@gmail.com
- Validation 2 étapes activée
- Mot de passe d'application dans .env (GMAIL_APP_PASSWORD)
- IMAP activé dans les paramètres Gmail

### Licence (optionnel — pour clients)
- AMAH_LICENSE_KEY dans .env
- Générée avec : py -3.13 tools/license.py <machine_uuid>
- Ou double-clic sur developpeur/generate_license.bat

## Modèle utilisé
- llama-3.3-70b-versatile (le plus capable de Groq)
- Défini dans config.py ligne MODEL

## Les 65 outils

### Fichiers — tools/files.py (7)
list_files, organize_folder, find_files, move_file, create_folder, read_file, get_folder_info

### Documents — tools/documents.py (4)
create_word, create_txt, create_pdf, read_document

### Recherche — tools/search.py (2)
web_search (DuckDuckGo), read_webpage

### Système — tools/system.py (3)
get_system_info, open_file, run_command (PowerShell sécurisé)

### Mémoire — tools/memory.py (3)
save_memory(content, category), get_memories(category), delete_memory(memory_id)

### Email — tools/email_tool.py (3)
read_emails(n), send_email(to, subject, body), search_emails(query)

### Navigateur — tools/browser.py (5)
open_browser(url), click_element(selector), fill_form(selector, value),
take_screenshot(path), get_page_text()

### Voix — tools/voice.py (1)
speak(text, speed)

### Notifications — tools/notifications.py (2)
send_notification(title, message, duration), set_reminder(message, minutes)

### Excel — tools/excel.py (3)
read_excel(path), create_excel(filename, headers, rows), append_to_excel(path, rows)

### Presse-papiers — tools/clipboard.py (2)
read_clipboard(), write_clipboard(text)

### Utilitaires — tools/utils.py (5)
calculate(expression), get_datetime(), add_days(days),
generate_password(length), convert_units(value, from, to)

### Archives — tools/archive.py (3)
zip_files(files, output), unzip_file(path, destination), list_archive(path)

### Images/Réseau — tools/image_tool.py (6)
screenshot_full(path), resize_image(path, width, height),
get_image_info(path), convert_image(path, format),
list_processes(top), get_network_info()

### Météo — tools/meteo.py (2)
get_weather(location), get_weather_simple(location)

### Traduction — tools/translator.py (2)
translate(text, to_lang), detect_language(text)

### QR Code — tools/qrcode_tool.py (1)
create_qrcode(text, output, size)

### Reconnaissance vocale — tools/voice_recognition.py (2)
listen(timeout, language), listen_continuous(duration, language)

### Planificateur — tools/scheduler.py (4)
create_daily_task(name, command, hour, minute), list_tasks(),
delete_task(name), run_task_now(name)

### Statistiques — tools/stats.py (2)
get_stats(days), reset_stats()

### Mises à jour — tools/updater.py (2)
check_update(), get_current_version()

### Licence — tools/license.py (1)
get_license_info()

## Architecture mémoire (amah_memory.db)
- Table conversations : historique auto de chaque échange
- Table memories : infos mémorisées explicitement
- Table tool_usage : statistiques d'utilisation des outils
- Au démarrage : 40 derniers messages rechargés automatiquement
- Trimming contexte : system prompt + 60 derniers messages max

## Interfaces disponibles
### Terminal (agent.py)
- Lance avec : py -3.13 agent.py
- Affiche les appels d'outils en temps réel

### Fenêtre graphique (gui.py)
- Lance avec : py -3.13 gui.py
- Écran de configuration au premier lancement (crée .env automatiquement)
- Horodatage sur chaque message
- Affichage des outils utilisés inline
- Barre d'état en bas (Prêt / réfléchit... / outil utilisé)
- Entrée multi-ligne (Shift+Entrée)
- Boutons Copier + Réinitialiser
- Raccourcis : Ctrl+R reset, Ctrl+C copier, Échap vider

## Système de licence
- Offline — pas besoin de serveur
- Clé liée au Machine UUID Windows de chaque PC
- Génération : py -3.13 tools/license.py <machine_uuid>
- Ou : double-clic developpeur/generate_license.bat
- Clé secrète dans tools/license.py (_SECRET)
- Voir developpeur/GUIDE_LICENCE.md pour le détail complet

## Distribution clients
Le dossier dist/ contient tout ce qu'il faut livrer :
- Amah Agent.exe (114 Mo, standalone, 65 outils)
- .env (Gmail pré-configuré, Groq à renseigner par le client)
- installer_navigateur.bat (Chromium, une seule fois)
- Guide_Installation_Client.docx (guide Word professionnel)

## Sécurité
- run_command bloque : rm -rf, del /f, format, shutdown, net user, reg delete
- Clé API dans .env (jamais dans le code ni dans le .exe)
- Mot de passe Gmail dans .env (jamais dans le code)
- .env.example ne contient jamais de vraies credentials
- Clé de licence liée au hardware (non transférable)

## Etat — Session 1 (28/05/2026)
- [x] 16 outils fonctionnels, interface terminal Rich
- [x] Bugs corrigés (tool_calls None, args null, chemins, ddgs)

## Etat — Session 2 (28/05/2026)
- [x] Interface graphique tkinter, raccourci bureau
- [x] Mémoire SQLite (conversations + memories)
- [x] 3 outils mémoire

## Etat — Session 3 (28-29/05/2026)
- [x] Packaging .exe PyInstaller, écran config premier lancement
- [x] Email Gmail SMTP/IMAP (3 outils)
- [x] Navigation web Playwright (5 outils)
- [x] Guide installation clients, installer_navigateur.bat
- [x] 27 outils au total

## Etat — Session 4 (29/05/2026)
- [x] Refactorisation : TOOL_FUNCTIONS centralisé dans tools/__init__.py
- [x] Trimming contexte : max 60 messages
- [x] Mémoire augmentée à 40 messages
- [x] Voix (synthèse Windows), notifications, rappels
- [x] Excel (3 outils), presse-papiers, calcul, date, archives, images
- [x] Réseau, processus, météo, traducteur, QR code
- [x] Reconnaissance vocale, planificateur Windows
- [x] Statistiques d'usage, mises à jour auto, licence offline
- [x] Interface améliorée : horodatage, outils inline, barre état, multi-ligne
- [x] Icône vectorielle professionnelle (A doré sur fond sombre)
- [x] Documentation Word complète, guide client Word
- [x] Dossier developpeur/ avec 5 guides techniques
- [x] 65 outils au total — .exe 114 Mo

## Prochaines améliorations possibles
- [ ] Activer la vérification de licence au démarrage (actuellement optionnelle)
- [ ] Héberger version.json pour les mises à jour automatiques
- [ ] Outil Google Calendar (agenda)
- [ ] Synthèse vocale mode mains libres (listen + speak en boucle)
- [ ] Connexion Telegram bot
- [ ] Dashboard journalier automatique
