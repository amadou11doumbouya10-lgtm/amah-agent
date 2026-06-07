# Brief — Projet Amah Agent
*Dernière mise à jour : 07/06/2026 — Version 1.4.1*

## Contexte
Agent IA local sur PC Windows — **78 outils** — version commerciale prête.
Cerveau : Groq API avec routage de modèle automatique (8B / 70B).
Interfaces : terminal Rich + fenêtre graphique tkinter + interface vocale HUD animée.
Python 3.13 · PyInstaller → .exe ~130 Mo standalone.
Email officiel : contact.amah.officiel@gmail.com
GitHub : github.com/amadou11doumbouya10-lgtm/amah-agent
Portfolio : amadou11doumbouya10-lgtm.github.io/-theamah-streaming/portfolio.html

---

## Nouveautés v1.4.1 (07/06/2026)
- Fix routage outils : normalisation des accents (météo/traduction → get_weather_simple)
- Sécurité tool routing renforcée
- Kit_Client_Amah recompilé avec gui.py (interface stable)

## Nouveautés v1.4.0 (05/06/2026)

### 11 nouveaux outils (inspirés de Mark XXXIX)

**Hardware (tools/computer_settings.py) — 6 outils**
- `set_volume(level)` / `get_audio_level()` — WinMM API via PowerShell + fichier .ps1 temp
- `mute_audio()` — bascule muet via keybd_event VK_VOLUME_MUTE
- `set_brightness(level)` / `get_brightness()` — WMI WmiMonitorBrightness
- `wifi_toggle(enable)` — netsh interface set

**Vision IA (tools/screen_vision.py) — 1 outil**
- `analyze_screen(question)` — PIL ImageGrab → JPEG base64 → Groq llama-3.2-11b-vision-preview
- Compression automatique : thumbnail 1280x720, qualité 82%

**YouTube (tools/youtube_tool.py) — 2 outils**
- `open_youtube(query)` — webbrowser.open YouTube search URL
- `search_youtube(query)` — DuckDuckGo site:youtube.com, sans ouvrir le navigateur

**Vols (tools/flight_finder.py) — 1 outil**
- `search_flights(from, to, date)` — DuckDuckGo résultats + webbrowser Google Flights

**Planificateur multi-étapes (tools/planner.py) — 1 outil**
- `create_plan(goal)` — Groq 70B + JSON mode → plan structuré max 6 étapes
- Format : `{"objectif": ..., "etapes": [{"n", "outil", "desc", "params"}], "note": ...}`

### Interface vocale HUD animée (voice_ui.py)

Nouveau fichier `voice_ui.py` — classe `VoiceWindow` :
- Canvas tkinter 420x500, animation 20fps via `after(50, ...)`
- Éléments : orbe central (pulsant), 3 anneaux (rotatifs), ligne radar, barres audio (18 barres)
- États colorés : ECOUTE (or), TRAITEMENT (cyan), ERREUR (rouge)
- Interpolation couleurs via `_hex_blend(c1, c2, t)`
- Thread daemon → `listen(timeout=8)` → résultat → ferme et envoie
- `gui._voice_mode = True` → après réponse, Amah parle automatiquement (220 chars)

### Améliorations GUI (gui.py)
- Monitoring CPU/RAM : thread daemon psutil, `after(0, ...)` toutes les 2s, code couleur vert/or/rouge
- Effet machine à écrire : 60 ticks × 20ms = ~1.2s total, chunk proportionnel à la longueur
- Bouton [◎] micro : ouvre VoiceWindow + active _voice_mode
- Bouton [+] pièce jointe : filedialog → insère le chemin dans l'entrée
- Statuts colorés : "Pret" → vert, "reflechit" → or, "Erreur" → rouge
- Règle MONO-APPEL dans le system prompt (inspiré de Mark XXXIX)

---

## Architecture

### Routage outils (gui.py → _WORD_TO_CAT)
120+ mots-clés mappés vers 17 catégories :
`fichiers | documents | internet | email | memoire | systeme | utils | data | media | images | info | planif | hardware | vision | youtube | flights | planner`

### Routage modèle (gui.py → _chat())
```python
if is_simple:   model = "llama-3.1-8b-instant"   # questions ≤6 mots
else:           model = "llama-3.3-70b-versatile"  # tâches avec outils
```

### Rotation clés API
- GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3 dans .env
- Bascule automatique sur 429 → clé suivante → backoff 1/2/4s
- 3 clés = 300 000 tokens/jour ≈ 200 appels/jour

---

## Les 78 outils (source unique : tools/__init__.py)

| Catégorie | Nb | Fichier |
|---|---|---|
| Fichiers/dossiers | 9 | tools/files.py |
| Documents Word/PDF/TXT | 4 | tools/documents.py |
| Recherche web (cache LRU) | 2 | tools/search.py |
| Système Windows | 3 | tools/system.py |
| Mémoire SQLite | 3 | tools/memory.py |
| Email Gmail SMTP/IMAP | 3 | tools/email_tool.py |
| Navigateur Chrome | 5 | tools/browser.py |
| Synthèse vocale | 1 | tools/voice.py |
| Reconnaissance vocale | 2 | tools/voice_recognition.py |
| Notifications + rappels | 2 | tools/notifications.py |
| Excel | 3 | tools/excel.py |
| Presse-papiers | 2 | tools/clipboard.py |
| Calcul/date/password | 5 | tools/utils.py |
| Archives ZIP | 3 | tools/archive.py |
| Images/réseau/processus | 6 | tools/image_tool.py |
| Météo | 2 | tools/meteo.py |
| Traduction | 2 | tools/translator.py |
| QR Code | 1 | tools/qrcode_tool.py |
| Planificateur Windows | 4 | tools/scheduler.py |
| Statistiques | 2 | tools/stats.py |
| Mises à jour | 2 | tools/updater.py |
| Licence offline | 1 | tools/license.py |
| Hardware (volume/luminosité/WiFi) | 6 | tools/computer_settings.py ← NEW |
| Vision IA écran | 1 | tools/screen_vision.py ← NEW |
| YouTube | 2 | tools/youtube_tool.py ← NEW |
| Vols | 1 | tools/flight_finder.py ← NEW |
| Planification multi-étapes | 1 | tools/planner.py ← NEW |

---

## Sécurité
- PowerShell : 14 mots-clés bloqués + 5 caractères interdits
- computer_settings : subprocess direct (pas run_command) → ExecutionPolicy Bypass sur .ps1 temp
- screen_vision : image envoyée à Groq uniquement (pas stockée)
- planner : appelle Groq indépendamment (clé lue depuis .env)
- Tool results : tronqués 2000 chars mémoire vive, 800 chars DB
- Licence : HMAC-SHA256 lié au Machine UUID Windows

---

## Distribution client (v1.4.1)
```
dist/  ← Kit complet prêt à livrer
├── Amah Agent.exe          (~150 Mo, v1.4.1, 79 outils)
├── .env                    (Gmail configuré, Groq + Licence à renseigner)
├── installer_navigateur.bat (Chrome, une seule fois)
└── GUIDE_INSTALLATION.md   (guide mis à jour v1.4.1)
```

---

## Futur
- Activer vérification licence fail-closed sur ventes
- Licence entreprise volume (une clé → N postes)
- Google Calendar (agenda)
- Mode mains libres (listen + speak en boucle, bouton micro permanent)
- Streaming Groq dans tkinter
- Dashboard journalier automatique
- Connexion Telegram bot
