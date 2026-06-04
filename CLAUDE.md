# Amah Agent Local

## Présentation
Agent IA local sur PC Windows. Cerveau : Groq (Llama 3.3, gratuit). 65 outils réels.
Projet séparé du chatbot web (avatar Amah). Usage : privé + commercial.
Email officiel Amah : contact.amah.officiel@gmail.com
Version actuelle : **v1.3.0**

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
├── recreate_ico.py           ← Recrée le .ico depuis le logo SVG hexagone
├── convert_logo.py           ← Convertit le SVG hexagone en PNG + ICO
├── amah.ico                  ← Icône officielle hexagone (A doré + œil cyan)
├── amah_logo_hex.png         ← Logo hexagone PNG 680x680
├── version.json              ← Version actuelle pour les mises à jour auto
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
│   ├── GUIDE_LICENCE_COMPLET.docx
│   ├── GUIDE_BUILD.md
│   ├── GUIDE_MISE_A_JOUR.md
│   ├── GUIDE_AJOUT_OUTIL.md
│   └── generate_license.bat
├── idees/                    ← Notes et idées du projet
├── analyse-ia/               ← Briefs pour analyse externe par d'autres IA
├── voix/                     ← Scripts et fichiers vidéos de présentation
├── dist/                     ← Dossier de distribution (généré par build.bat)
│   ├── Amah Agent.exe        (125 Mo, standalone, 65 outils, logo hexagone)
│   ├── .env                  (Gmail pré-configuré, Groq à renseigner)
│   ├── installer_navigateur.bat
│   └── GUIDE_INSTALLATION.md
├── .env                      ← Clé API Groq + Gmail + Licence (NE PAS partager)
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
- Rotation 3 clés : GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3 → 200 appels/jour

### Gmail (optionnel)
- Compte : contact.amah.officiel@gmail.com
- Validation 2 étapes activée
- Mot de passe d'application dans .env (GMAIL_APP_PASSWORD)
- IMAP activé dans les paramètres Gmail

### Licence (obligatoire pour clients)
- AMAH_LICENSE_KEY dans .env
- Générée avec : py -3.13 tools/license.py <machine_uuid>
- Ou double-clic sur developpeur/generate_license.bat
- Clé secrète dans .env (AMAH_LICENSE_SECRET)

## Modèles utilisés (routage automatique)
- **Questions simples** (≤6 mots, salutation) : `llama-3.1-8b-instant` (~0.3s)
- **Tâches avec outils** : `llama-3.3-70b-versatile` (~2s)
- Défini dans gui.py → `_chat()` + constante `MODEL` dans config.py

## Les 65 outils
### Fichiers — tools/files.py (7)
list_files, organize_folder, find_files, move_file, create_folder, read_file, get_folder_info

### Documents — tools/documents.py (4)
create_word, create_txt, create_pdf, read_document

### Recherche — tools/search.py (2)
web_search (DuckDuckGo + cache LRU 10min), read_webpage

### Système — tools/system.py (3)
get_system_info, open_file, run_command (PowerShell sécurisé)

### Mémoire — tools/memory.py (3)
save_memory(content, category), get_memories(category), delete_memory(memory_id)

### Email — tools/email_tool.py (3)
read_emails(n), send_email(to, subject, body), search_emails(query)
Auth : SMTP/IMAP + mot de passe application. Tri par date UTC + priorité emails perso.

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
- Table conversations : historique auto de chaque échange (session_id, role, content)
- Table memories : infos mémorisées explicitement (category, content)
- Table tool_usage : statistiques d'utilisation des outils
- Au démarrage : 10 derniers messages rechargés automatiquement
- Trimming contexte API : [system] + 40 derniers messages max
- Troncature tool_results : 2000 chars en mémoire vive, 800 chars en DB

## Optimisations tokens (v1.3)
- Descriptions outils compactes : 16 914 chars (~4 228 tokens)
- Routeur d'intention : 90+ mots-clés → 8-12 outils ciblés par appel
- DEFAULT_TOOLS (12 outils) si aucun mot-clé détecté
- Tokens/appel typique : ~1 500 (vs ~13 000 avant)
- Appels/jour avec 3 clés : ~200

## Interfaces disponibles
### Terminal (agent.py)
- Lance avec : py -3.13 agent.py
- Affiche les appels d'outils en temps réel

### Fenêtre graphique (gui.py)
- Lance avec : py -3.13 gui.py
- Écran de configuration premier lancement (3 clés Groq + licence + Gmail)
- Horodatage, outils affichés après réponse, barre état, multi-ligne
- v1.3.0 visible sur tous les écrans

## Système de licence
- Offline HMAC-SHA256 lié au Machine UUID Windows
- Clé secrète dans .env (AMAH_LICENSE_SECRET)
- Génération : py -3.13 tools/license.py <machine_uuid>
- LicenseWindow intégrée dans SetupWindow (premier lancement)
- UUID affiché + bouton Copier dans l'écran de config

## Distribution clients
Le dossier dist/ contient tout ce qu'il faut livrer :
- Amah Agent.exe (125 Mo, standalone, 65 outils, v1.3.0)
- .env (Gmail pré-configuré, Groq + Licence à renseigner)
- installer_navigateur.bat (Chromium, une seule fois)
- GUIDE_INSTALLATION.md (guide complet)

## Sécurité
- run_command bloque : rm -rf, invoke-expression, wget, & && || ` $(
- Clé API dans .env (jamais dans le code ni dans le .exe)
- Mot de passe Gmail dans .env
- .env.example sans vraies credentials
- Clé de licence liée au hardware (non transférable)
- Tool results tronqués à 2000 chars (protection injection/fuites)

## GitHub
- Repo : github.com/amadou11doumbouya10-lgtm/amah-agent
- Profil : github.com/amadou11doumbouya10-lgtm
- Portfolio : amadou11doumbouya10-lgtm.github.io/-theamah-streaming/portfolio.html

## Etat — v1.3.0 (04/06/2026)
- [x] Routage modèle : 8B (questions simples) / 70B (tool use)
- [x] Logo hexagone officiel (SVG + PNG 680px + ICO recadré)
- [x] Email : tri par date UTC réelle + priorité emails personnels
- [x] Démarrage <1s (check Playwright sans lancer le moteur)
- [x] Tokens -75% : routeur 90+ mots-clés + descriptions compactes
- [x] 3 clés Groq en rotation automatique (200 appels/jour)
- [x] SetupWindow : 3 clés Groq + licence + Gmail en un écran
- [x] Version v1.3.0 sur tous les écrans (config, licence, header)
- [x] README profil GitHub + Portfolio mis à jour

## Prochaines améliorations possibles
- [ ] Activer vérification licence sur ventes (remplacer fail-open par fail-closed)
- [ ] Licence entreprise volume (une clé pour N postes)
- [ ] Google Calendar (agenda)
- [ ] Mode mains libres (listen + speak en boucle)
- [ ] Streaming réponse Groq dans tkinter
- [ ] Dashboard journalier automatique
- [ ] Connexion Telegram bot
