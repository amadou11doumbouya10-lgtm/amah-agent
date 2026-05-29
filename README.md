# 🤖 Amah Agent — Assistant IA Local pour Windows

<p align="center">
  <img src="amah_final_v2_border.png" width="120" alt="Amah Agent Logo"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/IA-Groq%20%7C%20Llama%203.3-orange" />
  <img src="https://img.shields.io/badge/Outils-65-gold" />
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
Il peut interagir concrètement avec le système — fichiers, emails, navigateur, Excel, voix — simplement en lui parlant en français.

> *"Organise mon bureau"* → Amah classe les fichiers.  
> *"Lis mes derniers emails"* → Amah ouvre Gmail et les lit.  
> *"Crée un rapport Word sur notre réunion"* → Amah génère le document.

Contrairement aux assistants en ligne, **Amah fonctionne localement**, les données restent sur le PC, et elle se souvient de tout entre les sessions.

---

## Fonctionnalités clés

| Catégorie | Ce qu'Amah peut faire |
|-----------|----------------------|
| 📁 **Fichiers** | Lister, organiser, chercher, déplacer, créer |
| 📄 **Documents** | Créer Word, PDF, TXT — les lire et résumer |
| 🌐 **Internet** | Recherche DuckDuckGo, lecture de pages web |
| 📧 **Email Gmail** | Lire, envoyer, chercher dans la boîte mail |
| 🌍 **Navigateur** | Piloter Chrome (clic, formulaire, screenshot) |
| 🗣️ **Voix** | Parler à voix haute, écouter le microphone |
| 📊 **Excel** | Lire, créer, modifier des fichiers Excel |
| 🧠 **Mémoire** | Se souvenir entre les sessions (SQLite) |
| 🔔 **Notifications** | Alertes Windows + rappels programmés |
| 🌤️ **Météo** | Température et prévisions (wttr.in) |
| 🌐 **Traduction** | 100+ langues (deep-translator) |
| 📦 **Archives** | Créer et extraire des fichiers ZIP |
| 🖼️ **Images** | Redimensionner, convertir, capturer l'écran |
| ⏰ **Planificateur** | Tâches automatiques Windows Task Scheduler |
| 🔐 **Licence** | Système de licence offline lié au hardware |

**Total : 65 outils opérationnels.**

---

## Interface

<table>
<tr>
<td width="50%">

### Fenêtre graphique (gui.py)
- Thème or/sombre personnalisé
- Horodatage sur chaque message
- Outils affichés en temps réel
- Barre d'état dynamique
- Entrée multi-ligne
- Raccourcis clavier

</td>
<td width="50%">

### Écran de configuration
- Premier lancement automatique
- Clé Groq + Gmail en un seul écran
- Crée le `.env` automatiquement
- Aucune manipulation de fichiers pour le client

</td>
</tr>
</table>

---

## Stack technique

```
Cerveau IA   : Groq API — llama-3.3-70b-versatile (gratuit, 14 400 req/jour)
Interface    : Python tkinter (natif, thème personnalisé)
Mémoire      : SQLite — conversations + mémoire explicite + stats
Email        : SMTP/IMAP Gmail (mot de passe d'application)
Navigateur   : Playwright + Chromium (headless=False)
Traduction   : deep-translator (Google Translate)
Excel        : openpyxl
Images       : Pillow
Voix         : Windows System.Speech (natif, sans dépendance)
Packaging    : PyInstaller → .exe standalone 114 Mo
```

---

## Architecture

```
amah-agent/
├── gui.py                    ← Interface graphique principale
├── agent.py                  ← Interface terminal
├── config.py                 ← 65 définitions d'outils + system prompt
├── tools/
│   ├── __init__.py           ← Source unique de TOOL_FUNCTIONS
│   ├── files.py / documents.py / search.py / system.py
│   ├── memory.py / email_tool.py / browser.py
│   ├── voice.py / notifications.py / excel.py
│   ├── clipboard.py / utils.py / archive.py / image_tool.py
│   ├── meteo.py / translator.py / qrcode_tool.py
│   ├── voice_recognition.py / scheduler.py / stats.py
│   ├── updater.py / license.py
│   └── ...
└── dist/
    └── Amah Agent.exe        ← Livrable client
```

**Principe clé :** `tools/__init__.py` est la source unique de `TOOL_FUNCTIONS`.  
Ajouter un outil = 3 fichiers à modifier, zéro duplication.

---

## Système de mémoire

```
amah_memory.db (SQLite)
├── conversations  → historique auto, 40 messages rechargés au démarrage
├── memories       → infos mémorisées explicitement (catégories)
└── tool_usage     → statistiques d'utilisation par outil
```

Le contexte API est tronqué intelligemment : `[system_prompt] + 60 derniers messages` — évite les dépassements de tokens sur les longues sessions.

---

## Installation (développement)

```bash
git clone https://github.com/ton-compte/amah-agent.git
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
- `Amah Agent.exe` — programme standalone (114 Mo)
- `.env` — configuration Gmail pré-remplie
- `installer_navigateur.bat` — Chrome (une seule fois)
- `Guide_Installation_Client.docx` — guide complet

---

## Licence

Ce projet est sous **licence propriétaire**.  
Le code source est partagé à titre de démonstration dans le cadre d'un portfolio.  
Toute utilisation commerciale nécessite une autorisation écrite.

---

## Contact

<p align="center">
  <a href="mailto:contact.amah.officiel@gmail.com">
    <img src="https://img.shields.io/badge/📧 contact.amah.officiel@gmail.com-Envoyer un email-C8A96E?style=for-the-badge&logo=gmail&logoColor=white" />
  </a>
</p>

> Pour toute question, démonstration ou demande commerciale : **contact.amah.officiel@gmail.com**

---

<p align="center">
  <i>Construit avec Python 3.13 · Groq API · Windows 11</i><br/>
  <b>📧 contact.amah.officiel@gmail.com</b>
</p>
