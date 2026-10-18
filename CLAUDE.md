# Amah Agent Local

## Présentation
Agent IA local sur PC Windows. Cerveau : Groq (gpt-oss-120b / gpt-oss-20b,
gratuit) + mode vocal temps réel Gemini Live. 99 outils réels.
Projet séparé du chatbot web (avatar Amah). Usage : privé + commercial.
Email officiel Amah : contact.amah.officiel@gmail.com
Version actuelle : **v1.5.2** (source unique : `CURRENT_VERSION` dans tools/updater.py)

## Structure
```
amah-agent/
├── agent.py                  ← Interface terminal (Rich, usage développeur, pipeline v0.x)
├── gui.py                    ← Interface graphique tkinter (clients, compilée dans le .exe)
├── voice_fullscreen.py       ← Interface vocale plein écran (HUD, mode normal + mode Live F9)
├── amah_listener.py          ← Mot de réveil "Amah" (widget discret, lance voice_fullscreen)
├── groq_client.py            ← Client Groq centralisé (singleton, rotation 3 clés sans
│                                 attente sur 429, repli dev sur proxy LiteLLM via
│                                 LITELLM_URL avec sonde de port, réparation gpt-oss)
├── gemini_tools.py           ← Sous-ensemble 33 outils + adaptateur schema pour Gemini Live
├── gemini_client.py          ← Session Gemini Live (audio temps réel + function calling)
├── config.py                 ← Modèles (MODEL, FINAL_MODEL), prompts, 99 définitions outils
├── system_prompt.txt         ← Texte du prompt système (~3 700 tokens avec le profil)
├── user_profile.txt          ← Profil personnel ajouté au prompt système (gitignoré,
│                                 jamais publié ; modèle : user_profile.example.txt)
├── create_shortcut.py        ← Crée le raccourci .lnk sur le bureau
├── amah_memory.db            ← Base SQLite mémoire persistante (auto-créée)
├── amah.spec                 ← Spec PyInstaller : embarque system_prompt.txt et tous
│                                 les modules tools/ (collect_submodules)
├── build.bat                 ← Lance la compilation .exe en une commande (efface dist/)
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
│   ├── __init__.py           ← SOURCE UNIQUE de TOOL_FUNCTIONS (99 outils) : registre qui
│   │                            corrige les noms gpt-oss, garde-fou + statistiques
│   │   ── Pipeline partagé (gui.py, voice_fullscreen.py, agent.py) ──
│   ├── tool_router.py        ← Routeur d'outils unique (4 niveaux, 0 à 12 outils)
│   ├── instant.py            ← Réponses sans IA : heure, date, calcul simple
│   ├── memory_context.py     ← Rappel de mémoire V0.2.4 ("tu te souviens…")
│   ├── guard.py              ← Confirmation des actions sensibles (refus par défaut)
│   │   ── Briques v0.x utilisées ──
│   ├── router_v03.py         ← Intentions précises (utilisées par tool_router)
│   ├── router_v04.py         ← Ne sert plus qu'à normaliser le texte heure/date
│   ├── memory_recall_v024.py ← Moteur de rappel mémoire (+ conversation_search_v022.py)
│   ├── context_v01.py        ← Contexte de conversation (agent.py)
│   ├── planner_v04.py        ← Comparaison/recommandation de produits (agent.py)
│   ├── planner_v06.py        ← Recherche approfondie, tout sujet (agent.py)
│   ├── executor_v03.py       ← Exécution vérifiée des plans (+ executor_v02, verification_v02)
│   ├── security_v02.py       ← Confirmation terminal (agent.py)
│   ├── capability_bridge_v01.py ← Workflows écran / navigateur+voix (agent.py)
│   ├── fastpath_v01.py       ← Capture, calcul, recherche directe (agent.py)
│   ├── voice_pipeline_v01.py ← Commande vocale dans le terminal (agent.py)
│   │   ── Outils ──
│   ├── files.py              ← Gestion fichiers/dossiers (7 outils)
│   ├── documents.py          ← Création Word/PDF/TXT, lecture (4 outils)
│   ├── search.py             ← Recherche DuckDuckGo + lecture page web (2 outils)
│   ├── system.py             ← Infos système, ouvrir fichiers, PowerShell (3 outils)
│   ├── memory.py             ← Mémoire SQLite persistante (3 outils)
│   ├── email_tool.py         ← Email Gmail SMTP/IMAP (3 outils)
│   ├── browser.py            ← Navigation web Playwright (5 outils)
│   ├── voice.py              ← Synthèse vocale edge-tts (voix Henri), repli
│   │                            Windows System.Speech si edge-tts echoue (1 outil)
│   ├── notifications.py      ← Notifications + rappels (2 outils)
│   ├── excel.py              ← Lecture/création Excel (3 outils)
│   ├── clipboard.py          ← Presse-papiers (2 outils)
│   ├── utils.py              ← Calcul, date, password, conversion (5 outils)
│   ├── archive.py            ← Archives ZIP (3 outils)
│   ├── image_tool.py         ← Images + réseau + processus (6 outils)
│   ├── meteo.py              ← Météo wttr.in (2 outils)
│   ├── translator.py         ← Traduction Google + repli gpt-oss-20b (2 outils)
│   ├── qrcode_tool.py        ← Génération QR codes (1 outil)
│   ├── voice_recognition.py  ← Reconnaissance vocale (2 outils)
│   ├── scheduler.py          ← Planificateur Windows (4 outils)
│   ├── stats.py              ← Statistiques d'usage (2 outils)
│   ├── updater.py            ← Mises à jour automatiques (2 outils)
│   ├── license.py            ← Système de licence offline (1 outil)
│   ├── computer_settings.py  ← Contrôle matériel : volume/luminosité/wifi (6 outils)
│   ├── screen_vision.py      ← Analyse écran par IA vision (1 outil)
│   ├── youtube_tool.py       ← YouTube + musique (3 outils)
│   ├── code_tools.py         ← Écriture/exécution/explication de code (3 outils)
│   ├── flight_finder.py      ← Recherche de vols (1 outil)
│   ├── planner.py            ← Plans IA multi-étapes + exécution auto (2 outils)
│   ├── games.py              ← Lanceur Steam/Epic Games (6 outils)
│   ├── webcam_vision.py      ← Analyse webcam par IA vision (1 outil)
│   └── webcam_guard.py       ← Auto-mute confidentialité webcam (2 outils)
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
├── dist/                     ← Généré par build.bat (format dossier)
│   ├── Amah-Agent-v1.5.2.zip ← À livrer au client
│   └── Amah Agent/
│       ├── Amah Agent.exe    (lanceur, logo hexagone)
│       ├── _internal/        (bibliothèques, system_prompt.txt — ne pas toucher)
│       ├── installer_navigateur.bat (Chromium via le Playwright embarqué)
│       └── GUIDE_INSTALLATION.md
├── benchmarks/               ← Mesures et vérifications (voir benchmarks/README.md) ;
│                                 à lancer depuis la racine : py -3.13 -m benchmarks.<nom>
├── archives/                 ← Anciennes versions (agent, tools/*_v0x, benchmarks
│                                 cassés, ancien .exe) — gitignoré, jamais publié
├── .env                      ← Clé API Groq + Gmail + Licence (NE PAS partager)
├── .env.example              ← Modèle à copier
└── requirements.txt          ← Dépendances Python
```

## Vérifications après chaque modification (sans appel IA)
```bash
py -3.13 -m benchmarks.benchmark_tool_router   # routeur : 95/95 attendu
py -3.13 -m benchmarks.benchmark_guard         # garde-fou : 15/15 attendu
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
- Limites gratuites par clé (gpt-oss-120b et gpt-oss-20b, chacun son quota) :
  8 000 tokens/minute, 200 000 tokens/jour, 1 000 requêtes/jour
- Le prompt système pèse ~3 700 tokens par appel → ~40 demandes avec outils
  par clé et par jour sur le 120b (la limite réelle est le quota journalier)
- Format : gsk_...
- Rotation 3 clés : GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3 (organisations
  Groq distinctes, quotas séparés) ; sur 429, bascule immédiate sur la clé suivante

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

### LiteLLM (optionnel, usage développeur uniquement)
- LITELLM_URL dans .env (ex: http://localhost:4000) active un proxy LiteLLM
  local en remplacement de Groq direct — quota illimité, failover multi-providers
- Invisible pour les clients : ils n'ont pas LITELLM_URL dans leur .env, donc
  toujours sur Groq direct
- Si le proxy n'est pas lancé, repli automatique sur Groq direct : une sonde
  de port (0,3 s) évite les ~16 s perdues au premier appel sous Windows
- Config/scripts de lancement (litellm_config.yaml, start_litellm.bat/py) sont
  gitignorés — jamais livrés aux clients

## Modèles utilisés
Llama 3.3 70B, Llama 3.1 8B et llama-4-scout ont été retirés par Groq (404).
- **Outils** : `openai/gpt-oss-120b` (`MODEL` dans config.py)
- **Conversation pure, reformulation après outils (agent.py), traduction de
  repli** : `openai/gpt-oss-20b` (`FINAL_MODEL`, quota séparé du 120b)
- **Vision (écran, webcam)** : `qwen/qwen3.8-27b` avec `reasoning_effort="none"`
- gpt-oss préfixe parfois les noms d'outils ("tool.get_system_info") :
  `resolve_tool_name` (tools/__init__.py) les corrige

## Pipeline d'un message (tools/tool_router.py, instant.py, memory_context.py)
1. **Réponse instantanée** (instant.py) : heure, date, calcul → 0 appel IA.
   Une durée ("dans 45 jours", "à 8 heures") n'est PAS une demande d'heure.
2. **Mémoire** (memory_context.py) : "tu te souviens…", "qu'est-ce qu'on avait
   dit sur…" → résumé sourcé de l'historique (réponse directe) ou injection
   dans le prompt pour une demande mixte.
3. **Routeur partagé** (tool_router.py), sans appel IA :
   - conversation pure (le message entier est une salutation/remerciement) → 0 outil
   - intentions précises de router_v03 → outils prioritaires
   - mots-clés par catégorie + extension des chemins (.xlsx → Excel…)
   - rien de reconnu → lot de 10 outils de lecture (jamais 0 outil : sans
     outil, gpt-oss répond à vide ou invente des noms d'outils)
   - au plus 12 outils, 8 en moyenne
   - Mesuré : 100 % sur 40 phrases d'audit et 55 phrases nouvelles (V0.4 : 15-20 %)
   - Tester sur des phrases DIFFÉRENTES des mots-clés : les anciens benchmarks
     reprenaient les phrases des motifs et mesuraient la mémorisation

## Les 99 outils
### Fichiers — tools/files.py (12)
list_files, organize_folder, find_files, move_file, create_folder, read_file,
write_file, edit_file, edit_pdf, get_folder_info, delete_file, summarize

### Documents — tools/documents.py (4)
create_word, create_txt, create_pdf, read_document

### Recherche — tools/search.py (2)
web_search (DuckDuckGo + cache LRU 10min), read_webpage

### Système — tools/system.py (4)
get_system_info, open_file, run_command (PowerShell filtré par expressions
régulières + confirmation), kill_process

### Mémoire — tools/memory.py (3)
save_memory(content, category), get_memories(category), delete_memory(memory_id)
get_memories cherche aussi dans le contenu (le modèle passe souvent un sujet au
lieu d'une catégorie) et masque les résumés internes `conversation_summary`.

### Email — tools/email_tool.py (4)
read_emails(n), send_email(to, subject, body), search_emails(query), draft_email(to, subject, body)
Auth : SMTP/IMAP + mot de passe application. Tri par date UTC + priorité emails perso.
Lecture en BODY.PEEK[] : ne marque pas les emails comme lus.

### Navigateur — tools/browser.py (7)
open_browser(url), click_element(selector), fill_form(selector, value),
take_screenshot(path), get_page_text(), click_text(texte), type_in_field(label, texte)
Les deux derniers ciblent par texte/label visible — pas de sélecteur CSS requis.

### Voix — tools/voice.py (1)
speak(text, speed) — edge-tts (voix Henri, fr-FR), repli Windows TTS hors ligne si echec

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
Google Traduction d'abord ; si Google refuse ("too many requests", fréquent),
repli sur gpt-oss-20b et Google mis en pause 10 min. detect_language passe par
le modèle. Textes longs découpés en morceaux de 4500 caractères.

### QR Code — tools/qrcode_tool.py (1)
create_qrcode(text, output, size)

### Reconnaissance vocale — tools/voice_recognition.py (2)
listen(timeout, language), listen_continuous(duration, language)

### Planificateur Windows — tools/scheduler.py (4)
create_daily_task(name, command, hour, minute), list_tasks(),
delete_task(name), run_task_now(name)

### Statistiques — tools/stats.py (2)
get_stats(days), reset_stats()
Chaque outil exécuté est enregistré automatiquement par tools/__init__.py.

### Mises à jour — tools/updater.py (2)
check_update(), get_current_version()

### Licence — tools/license.py (1)
get_license_info()

### Matériel (hardware) — tools/computer_settings.py (6)
set_volume, get_audio_level, mute_audio, set_brightness, get_brightness, wifi_toggle

### Vision écran — tools/screen_vision.py (1)
analyze_screen (Groq vision : qwen/qwen3.8-27b)

### YouTube et musique — tools/youtube_tool.py (3)
open_youtube, search_youtube, play_music

### Code — tools/code_tools.py (3)
write_code, run_code, explain_code

### Vols — tools/flight_finder.py (1)
search_flights (DuckDuckGo + Google Flights)

### Planification IA — tools/planner.py (2)
create_plan (génère un plan JSON multi-étapes), execute_plan (génère ET exécute
chaque étape, retry via Groq sur échec). Chaque étape sensible passe par le
garde-fou central (tools/guard.py), comme un appel direct.

### Jeux — tools/games.py (6)
open_steam, open_epic_games, list_installed_steam_games,
launch_game_steam, search_game_on_steam, install_game_steam

### Vision webcam — tools/webcam_vision.py (1)
analyze_webcam (capture + analyse Groq vision qwen3.8-27b, aperçu live "EN DIRECT")

### Confidentialité webcam — tools/webcam_guard.py (2)
start_auto_mute, stop_auto_mute (coupe le son si 2+ personnes détectées)

## Architecture mémoire (amah_memory.db)
- Table conversations : historique auto de chaque échange (session_id, role, content)
- Table memories : infos mémorisées explicitement (category, content) + résumés
  mis en cache par le rappel de mémoire (category = conversation_summary)
- Table tool_usage : statistiques d'utilisation des outils (alimentée automatiquement)
- Au démarrage : 10 derniers messages rechargés automatiquement
- Trimming contexte API : [system] + 40 derniers messages max
- Troncature tool_results : 2000 chars en mémoire vive, 800 chars en DB

## Coût en tokens
- Prompt système + profil : ~3 700 tokens par appel (le poste le plus lourd)
- Définitions d'outils : ~45 tokens par outil, 8 en moyenne par appel
- agent.py reformule les résultats d'outils avec un prompt court
  (RESPONSE_SYSTEM_PROMPT, config.py) sur gpt-oss-20b
- Piste d'économie principale : raccourcir system_prompt.txt / user_profile.txt

## Interfaces disponibles
### Terminal (agent.py) — usage développeur
- Lance avec : py -3.13 agent.py
- Affiche les appels d'outils et les diagnostics [ROUTER] / [MEMORY] / [PERF]
- Ordre de traitement : mémoire (si AMAH_MEMORY_V024=1) → heure/date →
  contexte (objectif, budget) → commande explicite ("exécute la commande …"
  ou commande reconnue comme ipconfig / Get-Process) → Capability Bridge
  (écran) → recherche approfondie (planner_v06) → FastPath → comparaison de
  produits (planner_v04) → routeur partagé → IA + outils → reformulation 20b
- Un seul tour d'outils par message : "fais X puis Y" n'exécute que X
- Confirmation des actions sensibles par question dans le terminal

### Fenêtre graphique (gui.py) — interface clients
- Lance avec : py -3.13 gui.py
- Écran de configuration premier lancement (3 clés Groq + licence + Gmail)
- Réponses instantanées, rappel de mémoire, routeur partagé, boucle d'outils
  multi-étapes, conversation pure en streaming sur gpt-oss-20b
- Fenêtre "Oui / Non" avant toute action sensible
- Horodatage, outils affichés après réponse, barre état, multi-ligne
- Monitoring CPU/RAM temps réel, machine à écrire, bouton [+] pièce jointe
- Bouton "⬡ Amah écoute" dans l'en-tête

### Interface vocale plein écran (voice_fullscreen.py)
- HUD futuriste (hexagone cyan animé, radar, barres audio)
- Boucle écoute → réponse → synthèse vocale entièrement automatique
- Réponses instantanées + routeur partagé + 3 outils locaux (mode Live,
  aperçu webcam, champ texte) ; conversation pure sur gpt-oss-20b
- F11 : plein écran/fenêtré, Échap ou "ferme" : quitter

### Mot de réveil "Amah" (amah_listener.py)
- Widget discret en bas à droite, détection par distance de Levenshtein
- Dire "Amah" lance automatiquement voice_fullscreen.py

### 🆕 Mode Live temps réel (Gemini, touche F9 dans voice_fullscreen.py)
- Bascule HUD violet "MODE LIVE · GEMINI"
- Connexion bidirectionnelle audio (gemini-2.5-flash-native-audio-latest,
  response_modalities=AUDIO, fr-FR)
- gemini_client.py : pont microphone (16kHz) <-> haut-parleurs (24kHz) via
  sounddevice + asyncio, exécution d'outils via run_in_executor
- gemini_tools.py : sous-ensemble de 33 outils "vocal-friendly" + adaptateur
  parameters_json_schema
- Interruption naturelle (l'utilisateur peut couper la parole d'Amah)
- Nécessite GEMINI_API_KEY dans .env (gratuite sur Google AI Studio)

## Système de licence
- Offline HMAC-SHA256 lié au Machine UUID Windows
- Clé secrète dans .env (AMAH_LICENSE_SECRET)
- Génération : py -3.13 tools/license.py <machine_uuid>
- LicenseWindow intégrée dans SetupWindow (premier lancement)
- UUID affiché + bouton Copier dans l'écran de config

## Distribution clients
`build.bat` produit `dist/Amah-Agent-v<version>.zip` (format dossier PyInstaller) :
- Le client dézippe le dossier `Amah Agent` et lance `Amah Agent.exe` ; le .exe
  ne fonctionne pas sans `_internal/` à côté de lui
- Format dossier choisi le 18/10/2026 : en fichier unique (208 Mo), le .exe
  décompressait ~480 Mo dans %TEMP% à chaque lancement (~46 s de démarrage) et
  ressemblait davantage à un logiciel malveillant pour les antivirus
- `.env`, `user_profile.txt` et `amah_memory.db` sont lus/créés à côté du .exe ;
  ne jamais zipper un dossier qui a déjà été lancé (il contiendrait la base)
- installer_navigateur.bat utilise le Playwright embarqué
  (`_internal/playwright/driver/node.exe`), sans Python chez le client
- Gros postes de la taille : Playwright ~109 Mo, OpenCV ~103 Mo,
  SpeechRecognition ~45 Mo, PyMuPDF ~42 Mo ; boto3/botocore exclus (inutiles)
- La mise à jour automatique (`download_update`, non branchée aujourd'hui)
  remplace un seul .exe : à adapter (zip) avant de l'activer

## Sécurité
- **Garde-fou central (tools/guard.py)** : chaque outil de TOOL_FUNCTIONS y
  passe, quelle que soit l'interface (gui, voix, mode Live, terminal,
  execute_plan). Demande l'accord pour : run_command, run_code, delete_file,
  move_file, organize_folder, edit_file, edit_pdf, kill_process, wifi_toggle,
  send_email, install_game_steam, tâches planifiées, delete_memory,
  reset_stats, start_auto_mute ; write_file seulement s'il écrase un fichier
  existant ; open_file seulement sur un exécutable (.exe, .bat, .ps1, .py…).
  Chaque interface enregistre son gestionnaire (set_confirm_handler) :
  fenêtre Oui/Non (tk_confirm_handler) dans gui.py et voice_fullscreen.py,
  question dans agent.py. **Sans gestionnaire enregistré, l'action est refusée.**
  Une fonction appelée directement depuis son module (ex. send_email du
  rapport de crash) ne passe pas par le garde-fou.
- run_command (tools/system.py) : filtre par expressions régulières sur les
  commandes ET leurs alias, indépendant de l'ordre des arguments (suppression,
  formatage, extinction, téléchargement, code dynamique, shells imbriqués,
  registre, comptes, services…). 22/22 commandes dangereuses testées bloquées,
  20/20 commandes courantes acceptées (dont Get-Date -Format). Une commande
  bloquée n'est pas soumise à confirmation.
- Ne jamais mettre de jeton dans l'URL du remote git : Git Credential Manager
  est configuré (credential.helper = manager)
- Clé API dans .env (jamais dans le code ni dans le .exe)
- Mot de passe Gmail dans .env
- .env.example sans vraies credentials
- Clé de licence liée au hardware (non transférable)
- Tool results tronqués à 2000 chars (protection injection/fuites)

## GitHub
- Repo : github.com/amadou11doumbouya10-lgtm/amah-agent
- Profil : github.com/amadou11doumbouya10-lgtm
- Portfolio : amadou11doumbouya10-lgtm.github.io/-theamah-streaming/portfolio.html

## Etat — v1.4.0 (05/06/2026)
- [x] Routage modèle : 8B (questions simples) / 70B (tool use)
- [x] Logo hexagone officiel (SVG + PNG 680px + ICO recadré)
- [x] Email : tri par date UTC réelle + priorité emails personnels
- [x] Démarrage <1s (check Playwright sans lancer le moteur)
- [x] Tokens -75% : routeur 90+ mots-clés + descriptions compactes
- [x] 3 clés Groq en rotation automatique (200 appels/jour)
- [x] SetupWindow : 3 clés Groq + licence + Gmail en un écran
- [x] Version v1.4.0 sur tous les écrans (config, licence, header)
- [x] **11 nouveaux outils** inspirés de Mark XXXIX :
  - Hardware : set_volume / mute_audio / set_brightness / get_brightness / wifi_toggle / get_audio_level
  - Vision IA : analyze_screen (Groq llama-3.2-vision)
  - YouTube : open_youtube / search_youtube
  - Vols : search_flights (DuckDuckGo + Google Flights)
  - Planificateur : create_plan (JSON multi-étapes, 70B)
- [x] GUI v1.4 : monitoring CPU/RAM temps réel, machine à écrire, bouton [+] pièce jointe
- [x] Règle mono-appel dans le system prompt
- [x] Routeur étendu : hardware / vision / youtube / flights / planner
- [x] Interface vocale plein écran Amah (voice_fullscreen.py) — HUD cyan, hexagone rotatif, radar, barres audio
- [x] **Mot de réveil "Amah"** (amah_listener.py) — widget coin bas-droit, détection SpeechRecognition, lance plein écran automatiquement
- [x] Bouton "⬡ Amah écoute" dans l'en-tête gui.py
- [x] 79 outils documentés dans docs/CAPACITES_AMAH.md
- [x] edit_pdf (PyMuPDF) — modification PDF en gardant la mise en page
- [x] Sécurité licence : fail-closed + secret dans .env
- [x] Fix write_file routing (plus d'erreur "not in request.tools")
- [x] amah.spec mis à jour : 5 nouveaux modules v1.4 + pymupdf

## Etat — v1.4.1 (07/06/2026)
- [x] Fix routage outils : normalisation des accents (météo/traduction → get_weather_simple)
- [x] Sécurité tool routing renforcée
- [x] Kit_Client_Amah recompilé avec gui.py (interface stable)

## Etat — v1.4.2 (08/06/2026)
- [x] **GroqClient centralisé** (groq_client.py) : singleton partagé par gui.py,
  tools/planner.py, tools/screen_vision.py et voice_fullscreen.py — fin des
  rotations de clés indépendantes (un outil pouvait rester bloqué sur une clé
  limitée pendant que gui.py tournait déjà sur la clé 2)
- [x] Fix bug prod découvert pendant la migration : analyze_screen utilisait un
  modèle vision décommissionné (llama-3.2-11b-vision-preview) →
  meta-llama/llama-4-scout-17b-16e-instruct
- [x] **Streaming des réponses simples** (8B, sans outils) : le texte
  apparaît au fur et à mesure au lieu d'attendre la réponse complète avant
  l'effet machine à écrire (_chat_stream dans gui.py) — latence perçue
  nettement réduite sur les échanges conversationnels courants
- [x] Fix bug chat : le placeholder "Amah réfléchit..." restait affiché
  au-dessus de chaque réponse (la marque Tk posée sur tk.END finissait après
  le texte inséré au lieu d'avant → corrigé avec "end-1c")
- [x] speak() rendu synchrone/bloquant avec les vraies erreurs PowerShell
  remontées (fin du fire-and-forget qui annonçait toujours un faux succès)
- [x] amah_listener.py : détection du mot de réveil "Amah" par distance de
  Levenshtein (moins de faux positifs/négatifs que l'ancienne heuristique)
- [x] System prompt : règle factuelle (web_search avant une réponse incertaine),
  règle de confirmation pour les outils sensibles (run_command/kill_process/
  delete_file/wifi_toggle), guidance sur la gestion des erreurs d'outils
- [x] Routeur (SIMPLE_PATTERNS) corrigé pour laisser passer les vraies
  questions factuelles vers le 70B + web_search au lieu de les confondre avec
  des phrases sociales

## Etat — v1.5.0 (11/06/2026)
- [x] **Lanceur de jeux** (tools/games.py, 6 outils) : open_steam,
  open_epic_games, list_installed_steam_games, launch_game_steam,
  search_game_on_steam, install_game_steam — détection via registre
  Windows, fichiers .acf et protocoles steam:// / com.epicgames.launcher://
- [x] **Vision webcam + confidentialité** (tools/webcam_vision.py,
  tools/webcam_guard.py, tools/webcam.py, 3 outils) : analyze_webcam
  (capture + analyse Groq vision, aperçu live "EN DIRECT"),
  start_auto_mute/stop_auto_mute (coupe le son si 2+ personnes détectées
  par la webcam pendant 3s, vie privée — désactivé par défaut)
- [x] **execute_plan** (tools/planner.py) : create_plan générait déjà un
  plan JSON, execute_plan le génère ET l'exécute étape par étape, avec
  retry via Groq en cas d'échec et confirmation obligatoire avant toute
  action sensible (run_command/kill_process/delete_file/wifi_toggle/
  start_auto_mute/send_email) — reprise via plan_id + confirmed=true
- [x] **Navigation web "comme un humain"** (tools/browser.py) :
  click_text(texte) et type_in_field(label, texte) ciblent les éléments
  par texte visible/label/placeholder via les locators accessibles
  Playwright (get_by_role/get_by_text/get_by_label/get_by_placeholder),
  sans sélecteur CSS — utilisables à voix haute
- [x] **Mode Live temps réel (Gemini)** — nouveau deuxième cerveau pour
  une vraie conversation orale (comme un appel) :
  - gemini_tools.py : sous-ensemble de 33 outils + adaptateur de schéma
    JSON (parameters_json_schema)
  - gemini_client.py : GeminiLiveSession, pont audio sounddevice/asyncio
    (micro 16kHz -> Gemini, Gemini -> haut-parleurs 24kHz), exécution des
    outils demandés par le modèle, interruption naturelle
  - voice_fullscreen.py : touche F9 bascule HUD violet "MODE LIVE · GEMINI",
    micro classique libéré proprement pendant le mode Live
  - GEMINI_API_KEY dans .env / .env.example
- [x] **99 outils au total**, documentés dans docs/CAPACITES_AMAH.md

## Etat — v1.5.1 (06/08/2026)
- [x] **Repli dev sur proxy LiteLLM** (groq_client.py) : LITELLM_URL dans
  .env bascule GroqClient sur un proxy LiteLLM local (quota illimité,
  failover multi-providers) — invisible pour les clients (pas de
  LITELLM_URL dans leur .env = toujours Groq direct). Repli automatique et
  silencieux sur Groq si le proxy n'est pas lancé (connexion refusée).
  Réparation `tool_use_failed` étendue au format d'erreur LiteLLM/OpenAI SDK
  (JSON extrait par comptage de profondeur d'accolades, pas de regex
  gourmande — le message LiteLLM contient du texte après le JSON qui
  cassait une regex `r'\{.*\}'`). Distinction quota journalier épuisé
  (fail immédiat, "TPD") vs rate-limit par minute (retry avec backoff).
  Badge `[Groq]`/`[LiteLLM]` dans la barre de statut de gui.py.
- [x] **Synthèse vocale edge-tts** (tools/voice.py) : voix Henri (fr-FR)
  via edge-tts au lieu de Windows System.Speech, avec repli automatique sur
  le TTS Windows hors ligne si edge-tts échoue (2 tentatives). Lecture MP3
  bloquante via COM System.Windows.Media.MediaPlayer.
- [x] **Traduction de textes longs** (tools/translator.py) : découpage
  automatique par paragraphes en morceaux de 4500 caractères pour respecter
  la limite ~5000 caractères de GoogleTranslator.
- [x] **max_tokens** 1024 → 4096 (gui.py, voice_fullscreen.py) : évite les
  réponses tronquées sur les tâches à plusieurs outils/étapes.
- [x] System prompt : règle "fichiers code" (write_file/edit_file
  obligatoire pour .html/.css/.js/.py/.json/.md — create_txt réservé aux
  notes brutes, il ajoute ".txt" et casse les fichiers web/code) et règle
  "créateur" (ne citer Amadou Doumbouya que si on le demande explicitement,
  pas dans un "qui es-tu" générique).
- [x] Mot de réveil "Amah" (amah_listener.py) : seuils resserrés
  (energy_threshold 250→200, pause_threshold 0.5→0.25s) pour une détection
  plus rapide, reconnaissance fr-FR uniquement (fallback anglais retiré).
- [x] voice_fullscreen.py : retry silencieux sur coupure réseau passagère
  de la reconnaissance vocale avant de signaler une vraie panne ; fix
  race condition au basculement mode Live (flag `_live_mode` posé de façon
  synchrone au lieu d'attendre `root.after`, qui pouvait laisser le micro
  Groq et le micro Gemini ouverts simultanément).
- [x] gemini_client.py : voix Gemini Live changée pour "Charon".
- [x] requirements.txt : ajout de `edge-tts` et `openai` (dépendances
  manquantes, utilisées respectivement par tools/voice.py et le mode
  LiteLLM de groq_client.py).

## Etat — v1.5.2 (14/10/2026, audit complet + corrections)
Audit du 14/10/2026 : https://claude.ai/artifact/4buALzsuDviWsESJN29AwZ
- [x] **Modèles** : passage à gpt-oss-120b / gpt-oss-20b et qwen3.8-27b
  (Llama 3.3, Llama 3.1 et llama-4-scout retirés par Groq)
- [x] **Vitesse** : requêtes avec outils de 27-71 s à 2-8 s (rotation immédiate
  des clés sur 429, prompt court pour la reformulation, sonde LiteLLM)
- [x] **Sécurité** : garde-fou central tools/guard.py + filtre run_command
  réécrit (gui.py n'avait aucune confirmation réelle)
- [x] **read_emails** réparé (renvoyait 0 email depuis la v1.4.2, commit e9ea55a)
- [x] **Routeur partagé** tools/tool_router.py pour les 3 interfaces : 100 %
  sur 95 phrases de test (V0.4 : 15-20 %, ancien routeur gui.py : 80-85 %)
- [x] **gui.py** : réponses instantanées et rappel de mémoire V0.2.4
  (tools/instant.py, tools/memory_context.py, partagés avec agent.py)
- [x] **agent.py** : "je veux…", "lance X", "analyse le fichier…", "compare…",
  "capture d'écran", "dans 45 jours" ne sont plus détournés ;
  32/37 scénarios réussis (11/37 avant)
- [x] Noms d'outils gpt-oss corrigés, statistiques alimentées, version unique
  1.5.2, traduction de repli par IA, Excel/Word/PDF lisibles par read_file
- [x] Bug gui.py corrigé : toute erreur Groq s'affichait en "cannot access
  local variable 'repair_tool_use_failed'" (import local, depuis 9fe1cc1)
- [ ] Refaire la série complète de scénarios gui.py (interrompue par le quota
  journalier Groq le 14/10)
- [x] Rangement : benchmarks dans benchmarks/ (+ benchmark_tool_router et
  benchmark_guard, sans appel IA), sauvegardes / ~24 tools/*_v0x morts /
  benchmarks cassés dans archives/ (gitignoré)
- [x] **.exe v1.5.2 recompilé au format dossier** : system_prompt.txt embarqué
  (le .exe aurait planté), 11 modules d'outils qui manquaient inclus
  (collect_submodules), boto3 exclu. Zip 193 Mo ; démarrage 13-17 s (46 s en
  fichier unique). installer_navigateur.bat sans Python (Playwright embarqué).
  GUIDE_INSTALLATION.md mis à jour (dézipper, garder le dossier entier).

## Prochaines améliorations possibles
- [ ] Démarrage du .exe (13 s) : charger OpenCV / Playwright / NumPy à la
  demande plutôt qu'à l'ouverture de gui.py
- [ ] Raccourcir le prompt système (~3 700 tokens/appel) : principal levier
  pour dépasser ~40 demandes avec outils par clé et par jour
- [ ] agent.py : enchaîner plusieurs outils ("fais X puis Y") comme gui.py
- [ ] Recherche web plus fiable (DuckDuckGo limite les requêtes, résultats peu pertinents)
- [ ] Synthèse vocale plus rapide (~8 s pour une phrase courte : démarrage PowerShell)
- [ ] Licence entreprise volume (une clé pour N postes)
- [ ] Google Calendar (agenda)
- [ ] Dashboard journalier automatique
- [ ] Connexion Telegram bot
- [ ] Wake word hors ligne (Porcupine / openWakeWord) pour ne pas dépendre de Google Speech API
