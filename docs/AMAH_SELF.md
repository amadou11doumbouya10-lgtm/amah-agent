# Amah — Fiche de connaissance de soi (v1.5.0)

> Fichier condensé, a lire avec `read_file` avant de repondre a une question sur
> tes propres ameliorations/roadmap/fonctionnalites possibles. Base tes
> reponses sur CE document (architecture et roadmap reelles), pas sur des
> idees generiques de "roadmap assistant IA".

## Stack reelle
Python 3.13, Groq API (Llama 3.3 70B pour les outils, Llama 3.1 8B pour le
simple), Gemini Live (mode vocal temps reel), tkinter (GUI), SQLite (memoire),
Playwright (navigateur), openpyxl (Excel), python-docx/fpdf2 (documents),
PyMuPDF (PDF), psutil (systeme). **Pas de TensorFlow/PyTorch/CNN/RNN/modele
entraine en local** — toute l'"intelligence" vient des appels API Groq/Gemini.

## Les 101 outils (par categorie)
- Fichiers (12) : list_files, organize_folder, find_files, move_file,
  create_folder, read_file, write_file, edit_file, edit_pdf, get_folder_info,
  delete_file, summarize
- Documents (4) : create_word, create_txt, create_pdf, read_document
- Recherche web (2) : web_search, read_webpage
- Systeme (4) : get_system_info, open_file, run_command, kill_process
- Memoire (3) : save_memory, get_memories, delete_memory
- Email (4) : read_emails, send_email, search_emails, draft_email
- Navigateur (7) : open_browser, click_element, fill_form, take_screenshot,
  get_page_text, click_text, type_in_field
- Voix (2) : speak, read_aloud (lit une page web entiere a voix haute)
- Notifications (2) : send_notification, set_reminder
- Briefing (1) : morning_briefing (date, meteo, emails importants non lus, taches ;
  affiche seul au premier lancement du jour, "fais-moi le point" le redonne)
- Excel (3) : read_excel, create_excel, append_to_excel
- Presse-papiers (2) : read_clipboard, write_clipboard
- Utilitaires (5) : calculate, get_datetime, add_days, generate_password,
  convert_units
- Archives (3) : zip_files, unzip_file, list_archive
- Images/Reseau (6) : screenshot_full, resize_image, get_image_info,
  convert_image, list_processes, get_network_info
- Meteo (2) : get_weather, get_weather_simple
- Traduction (2) : translate, detect_language
- QR Code (1) : create_qrcode
- Reconnaissance vocale (2) : listen, listen_continuous
- Planificateur Windows (4) : create_daily_task, list_tasks, delete_task,
  run_task_now
- Statistiques (2) : get_stats, reset_stats
- Mises a jour (2) : check_update, get_current_version
- Licence (1) : get_license_info
- Materiel (6) : set_volume, get_audio_level, mute_audio, set_brightness,
  get_brightness, wifi_toggle
- Vision ecran (1) : analyze_screen
- YouTube/Musique (3) : open_youtube, search_youtube, play_music
- Code (3) : write_code, run_code, explain_code
- Vols (1) : search_flights
- Planification IA (2) : create_plan, execute_plan
- Jeux (6) : open_steam, open_epic_games, list_installed_steam_games,
  launch_game_steam, search_game_on_steam, install_game_steam
- Vision webcam (1) : analyze_webcam
- Confidentialite webcam (2) : start_auto_mute, stop_auto_mute

## Limitations connues actuellement
- Pas de synchronisation agenda (Google Calendar) : `set_reminder` n'est pas
  persistant, `get_memories` sert de pis-aller pour le panneau MEMOIRE de
  l'interface vocale.
- Quota Groq limite (~200 appels/jour avec 3 cles en rotation) — pas de modele
  local de secours.
- Mot de reveil "Amah" depend de Google Speech API (en ligne).
- Pas d'integration Microsoft 365 / Outlook / Teams.
- Pas d'apprentissage automatique des habitudes utilisateur (toute
  "personnalisation" passe par `save_memory`/`get_memories`, donc explicite).

## Roadmap deja identifiee (a privilegier dans les suggestions)
- Licence entreprise volume (une cle pour N postes)
- Google Calendar (agenda)
- Dashboard journalier automatique
- Connexion Telegram bot
- Wake word hors ligne (Porcupine / openWakeWord), pour ne plus dependre de
  Google Speech API
