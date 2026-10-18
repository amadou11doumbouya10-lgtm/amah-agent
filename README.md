# Amah Agent — Assistant IA Local pour Windows

<p align="center">
  <img src="amah_logo_hex.png" width="120" alt="Amah Agent Logo"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/IA-Groq%20%7C%20Llama%203.3-orange" />
  <img src="https://img.shields.io/badge/Mode%20Live-Gemini-9B59B6" />
  <img src="https://img.shields.io/badge/Outils-99-gold" />
  <img src="https://img.shields.io/badge/Version-1.5.0-C8A96E" />
  <img src="https://img.shields.io/badge/Platform-Windows%2011-0078D4?logo=windows" />
  <img src="https://img.shields.io/badge/Interface-tkinter-green" />
  <img src="https://img.shields.io/badge/Licence-Propriétaire-red" />
  <img src="https://img.shields.io/badge/Contact-contact.amah.officiel%40gmail.com-C8A96E?logo=gmail&logoColor=white" />
</p>

<p align="center">
  <b>📧 &nbsp;<a href="mailto:contact.amah.officiel@gmail.com">contact.amah.officiel@gmail.com</a></b>
</p>

---

## Présentation

**Amah Agent** est un assistant IA installé localement sur un PC Windows.  
Il peut interagir concrètement avec le système — fichiers, emails, navigateur, Excel, voix, YouTube, vols — simplement en lui parlant en français, à l'écrit ou à la voix.

> *"Organise mon bureau"* → Amah classe les fichiers.  
> *"Lis mes derniers emails"* → Amah ouvre Gmail et les lit.  
> *"Lance une vidéo YouTube sur Python"* → Amah ouvre YouTube.  
> *"Cherche un vol Paris→New York pour juillet"* → Amah ouvre Google Flights.  
> *"Règle le volume à 60%"* → Amah ajuste le son.  
> *"Lance Cyberpunk sur Steam"* → Amah ouvre le launcher et lance le jeu.  
> *"Amah, fais X, Y puis Z"* → execute_plan génère et exécute un plan multi-étapes automatiquement.

Contrairement aux assistants en ligne, **Amah fonctionne localement**, les données restent sur le PC, et elle se souvient de tout entre les sessions.

---

## Fonctionnalités clés

| Catégorie | Ce qu'Amah peut faire |
|-----------|----------------------|
| 📁 **Fichiers** | Lister, organiser, chercher, déplacer, lire, écrire, éditer, supprimer, résumer |
| 📄 **Documents** | Créer Word, PDF, TXT — les lire et résumer |
| 🌐 **Internet** | Recherche DuckDuckGo, lecture de pages web |
| 📧 **Email Gmail** | Lire, envoyer, chercher, rédiger un brouillon |
| 🌍 **Navigateur** | Profil persistant (cookies/connexions conservées), clic/formulaire/screenshot, navigation par texte visible (`click_text`, `type_in_field`) sans sélecteur CSS |
| 🎙️ **Interface vocale** | HUD animé style Amah — parle, Amah répond à voix haute |
| 🗣️ **Mode Live (Gemini)** | Conversation orale temps réel (F9), interruption naturelle, 33 outils vocaux |
| 🔊 **Voix** | Synthèse vocale + reconnaissance micro + lecture complète d'une page web à voix haute |
| 📊 **Excel** | Lire, créer, modifier des fichiers Excel |
| 🧠 **Mémoire** | Se souvenir entre les sessions (SQLite) |
| 🔔 **Notifications** | Alertes Windows + rappels programmés |
| 🌤️ **Météo** | Température et prévisions (wttr.in) |
| 🌐 **Traduction** | 100+ langues (deep-translator) |
| 📦 **Archives** | Créer et extraire des fichiers ZIP |
| 🖼️ **Images** | Redimensionner, convertir, capturer l'écran |
| 👁️ **Vision IA** | Analyser l'écran par IA (Groq llama-4-scout) |
| 🔊 **Hardware** | Volume, luminosité, WiFi on/off |
| 🎬 **YouTube** | Ouvrir une vidéo, chercher, lancer de la musique |
| ✈️ **Vols** | Comparer des vols + ouvrir Google Flights |
| 🗂️ **Plan multi-étapes** | `create_plan` (générer) et `execute_plan` (générer ET exécuter, avec retry et confirmation pour les actions sensibles) |
| 💻 **Code** | Écrire, exécuter et expliquer du code |
| ⏰ **Planificateur** | Tâches automatiques Windows Task Scheduler |
| 🔐 **Licence** | Système de licence offline lié au hardware |
| 🎮 **Jeux** | Lancer/installer/chercher des jeux Steam, ouvrir Epic Games |
| 📷 **Vision webcam** | Analyser l'image webcam par IA + auto-mute confidentialité (coupe le son si plusieurs personnes détectées) |

**Total : 101 outils opérationnels.**

---

## Interface

<table>
<tr>
<td width="50%">

### Fenêtre graphique (gui.py)
- Thème or/sombre personnalisé
- Horodatage sur chaque message
- Outils affichés en temps réel
- Monitoring CPU/RAM en direct
- Streaming des réponses (texte progressif)
- Effet machine à écrire sur les réponses
- Bouton micro [◎] — interface vocale HUD animée
- Bouton [+] — joindre un fichier
- Raccourcis clavier

</td>
<td width="50%">

### Interface vocale HUD (voice_fullscreen.py)
- Fenêtre animée style Amah (orbe + anneaux rotatifs, jauges CPU/RAM, horloge, panneau MEMOIRE)
- États colorés : ECOUTE (or) / TRAITEMENT (cyan) / ERREUR (rouge)
- Barres audio animées pendant l'écoute
- Transcription affichée avant envoi
- Réponse automatique à voix haute
- Champ de saisie texte (Ctrl+T) pour écrire au lieu de parler
- **Mode Live Gemini (touche F9)** — HUD violet, conversation orale temps réel
  bidirectionnelle, interruption naturelle
- Mot de réveil **"Amah"** (amah_listener.py, détection Levenshtein)

</td>
</tr>
</table>

---

## Stack technique

```
Cerveau IA   : Groq API — llama-3.3-70b-versatile (tâches) / llama-3.1-8b-instant (questions simples)
Mode Live    : Gemini 2.5 Flash (native-audio) — conversation orale temps réel (F9), 33 outils
Vision IA    : Groq meta-llama/llama-4-scout-17b-16e-instruct (analyze_screen, analyze_webcam)
Plan IA      : Groq llama-3.3-70b + JSON mode (create_plan / execute_plan)
Client Groq  : groq_client.py — singleton partagé, rotation 3 clés, retry backoff (timeout + 503),
               repair_tool_use_failed() (récupère les pseudo-appels d'outils mal formés de Llama 3.3)
Interface    : Python tkinter (natif, thème or/sombre personnalisé)
Interface HUD: voice_fullscreen.py — canvas animé (orbe, anneaux, radar, barres audio, mode Live violet)
Mémoire      : SQLite — conversations + mémoire explicite + stats
Email        : SMTP/IMAP Gmail (mot de passe d'application)
Navigateur   : Playwright + Edge/Chromium, profil persistant (browser_profile/), navigation par
               texte visible (click_text/type_in_field)
Traduction   : deep-translator (Google Translate)
Excel        : openpyxl
Images       : Pillow
Voix sortie  : Windows System.Speech (natif, sans dépendance)
Voix entrée  : SpeechRecognition + Google STT (internet requis)
Audio Live   : sounddevice + asyncio (micro 16kHz <-> haut-parleurs 24kHz)
Hardware     : WinMM API + WMI + netsh via PowerShell
Packaging    : PyInstaller → .exe standalone ~150 Mo
```

---

## Architecture

```
amah-agent/
├── gui.py                    ← Interface graphique principale (chat + HUD)
├── voice_fullscreen.py       ← Interface vocale HUD plein écran animée (+ mode Live F9)
├── amah_listener.py          ← Détection mot de réveil "Amah" (Levenshtein)
├── agent.py                  ← Interface terminal
├── config.py                 ← 99 définitions d'outils (TOOLS_DEFINITIONS)
├── groq_client.py            ← Client Groq singleton (rotation clés, retry backoff, repair_tool_use_failed)
├── gemini_client.py          ← Session Gemini Live (pont audio micro/haut-parleurs, function calling)
├── gemini_tools.py           ← Sous-ensemble de 33 outils + adaptateur de schéma pour Gemini Live
├── system_prompt.txt         ← Texte du prompt système (éditable sans toucher au code)
├── docs/AMAH_SELF.md          ← Fiche condensée d'auto-connaissance (architecture, outils, roadmap)
├── tools/
│   ├── __init__.py           ← Source unique de TOOL_FUNCTIONS (101 outils, génération dynamique)
│   ├── files.py              ← Fichiers/dossiers (12 outils)
│   ├── documents.py          ← Word, PDF, TXT (4 outils)
│   ├── search.py             ← DuckDuckGo + lecture web (2 outils)
│   ├── system.py             ← Infos système, PowerShell (4 outils)
│   ├── memory.py             ← SQLite (conversations + memories) (3 outils)
│   ├── email_tool.py         ← Gmail SMTP/IMAP (4 outils)
│   ├── browser.py            ← Playwright Edge/Chromium, profil persistant (7 outils)
│   ├── voice.py              ← Synthèse vocale Windows (1 outil)
│   ├── voice_recognition.py  ← Reconnaissance vocale (2 outils)
│   ├── notifications.py      ← Notifications + rappels (2 outils)
│   ├── excel.py              ← Excel (3 outils)
│   ├── clipboard.py          ← Presse-papiers (2 outils)
│   ├── utils.py              ← Calcul/date/password (5 outils)
│   ├── archive.py            ← ZIP (3 outils)
│   ├── image_tool.py         ← Screenshot/images/réseau/processus (6 outils)
│   ├── meteo.py              ← Météo (2 outils)
│   ├── translator.py         ← Traduction (2 outils)
│   ├── qrcode_tool.py        ← QR codes (1 outil)
│   ├── scheduler.py          ← Planificateur Windows (4 outils)
│   ├── stats.py              ← Statistiques (2 outils)
│   ├── updater.py            ← Mises à jour (2 outils)
│   ├── license.py            ← Licence offline fail-closed (1 outil)
│   ├── computer_settings.py  ← Volume/luminosité/WiFi (6 outils)
│   ├── screen_vision.py      ← Vision écran IA (1 outil)
│   ├── youtube_tool.py       ← YouTube + musique (3 outils)
│   ├── code_tools.py         ← Écriture, exécution, explication code (3 outils)
│   ├── flight_finder.py      ← Vols + Google Flights (1 outil)
│   ├── planner.py            ← create_plan / execute_plan (2 outils)
│   ├── games.py              ← Lanceur Steam/Epic Games (6 outils)
│   ├── webcam_vision.py      ← Analyse webcam par IA (1 outil)
│   └── webcam_guard.py       ← Auto-mute confidentialité webcam (2 outils)
└── dist/
    └── Amah Agent.exe        ← Livrable client (~150 Mo)
```

**Principe clé :** `tools/__init__.py` génère `TOOL_FUNCTIONS` dynamiquement — ajouter un outil revient à inscrire son module et son nom dans une seule table.

---

## Système de mémoire

```
amah_memory.db (SQLite)
├── conversations  → historique auto, 40 messages rechargés au démarrage
├── memories       → infos mémorisées explicitement (catégories)
└── tool_usage     → statistiques d'utilisation par outil
```

---

## Installation (développement)

```bash
git clone https://github.com/amadou11doumbouya10-lgtm/amah-agent.git
cd amah-agent

pip install -r requirements.txt
py -3.13 -m playwright install chromium

copy .env.example .env
# Éditer .env avec ta clé Groq (console.groq.com)

py -3.13 gui.py
```

---

## Distribution client

```bash
build.bat   # Compile Amah Agent.exe (PyInstaller)
```

Le dossier `dist/` contient tout le livrable :
- `Amah Agent.exe` — programme standalone (~150 Mo)
- `.env` — configuration Gmail pré-remplie
- `installer_navigateur.bat` — Chrome (une seule fois)
- `GUIDE_INSTALLATION.md` — guide complet

---

## Historique des versions

| Version | Date | Nouveautés |
|---------|------|-----------|
| v1.5.0 | 11/06/2026 | 99 outils. Lanceur de jeux Steam/Epic (6 outils), vision webcam + auto-mute confidentialité (3 outils), execute_plan (exécution automatique de plan multi-étapes avec retry + confirmation), navigation web par texte visible (click_text/type_in_field), mode vocal temps réel Gemini Live (touche F9, 33 outils, interruption naturelle) |
| v1.4.2 | 08/06/2026 | Streaming réponses simples, GroqClient centralisé + retry timeout, fix vision (llama-4-scout), fix placeholder "réfléchit...", secret licence fail-closed, logging blocs except silencieux, TOOL_FUNCTIONS dynamique, system_prompt.txt externalisé, clé ElevenLabs migrée dans .env |
| v1.4.1 | 07/06/2026 | Fix routage outils (normalisation accents météo/traduction), sécurité tool routing renforcée |
| v1.4.0 | 05/06/2026 | +11 outils (hardware, vision, YouTube, vols, planificateur), interface vocale HUD animée, mot de réveil "Amah", monitoring CPU/RAM, effet machine à écrire |
| v1.3.0 | 04/06/2026 | Routage modèle 8B/70B, logo hexagone, email optimisé, tokens -75%, rotation 3 clés Groq |
| v1.2.0 | — | Sécurité PowerShell, mémoire SQLite, statistiques |
| v1.0.0 | — | Version initiale, 65 outils |

---

## Licence

Ce projet est sous **licence propriétaire**.  
Le code source est partagé à titre de démonstration dans le cadre d'un portfolio.  
Toute utilisation commerciale nécessite une autorisation écrite.

---

## Contact

<p align="center">
  <a href="mailto:contact.amah.officiel@gmail.com">
    <img src="https://img.shields.io/badge/contact.amah.officiel@gmail.com-Envoyer un email-C8A96E?style=for-the-badge&logo=gmail&logoColor=white" />
  </a>
</p>

> Pour toute question, démonstration ou demande commerciale : **contact.amah.officiel@gmail.com**

---

<p align="center">
  <i>Construit avec Python 3.13 · Groq API · Windows 11</i><br/>
  <b>📧 contact.amah.officiel@gmail.com</b>
</p>
