# Amah Agent — Toutes les capacités (v1.4.2)

> **79 outils réels** • Fonctionne hors ligne • Windows 11 • Mis à jour le 07/06/2026

---

## Vue d'ensemble

Amah Agent est une assistante IA locale qui s'exécute directement sur ton PC Windows.
Elle comprend le français naturel et peut agir sur ton ordinateur via 79 outils réels,
regroupés en 14 catégories.

**Exemples de phrases :**
- *"Organise mon bureau"*
- *"Envoie un email à Jean avec le résumé du projet"*
- *"Cherche le prix des vols Paris → New York pour le 20 juillet"*
- *"Règle le volume à 40%"*
- *"Qu'est-ce que tu vois sur mon écran ?"*

---

## 1. Fichiers et Dossiers — 10 outils

Amah peut lire, créer, déplacer, modifier et organiser tous tes fichiers.

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `list_files` | Liste le contenu d'un dossier | *"Montre-moi mon bureau"* |
| `find_files` | Cherche des fichiers par nom ou extension | *"Trouve tous les PDF dans mes Documents"* |
| `organize_folder` | Classe automatiquement par type (Images, Vidéos, Documents…) | *"Organise mon dossier Téléchargements"* |
| `move_file` | Déplace ou renomme un fichier | *"Déplace rapport.pdf vers Documents"* |
| `create_folder` | Crée un nouveau dossier | *"Crée un dossier Projets 2026 sur le bureau"* |
| `read_file` | Lit le contenu d'un fichier texte | *"Lis le fichier notes.txt"* |
| `write_file` | Écrit ou crée un fichier texte (HTML, Python, JS, CSS…) | *"Crée un fichier index.html avec ce code"* |
| `edit_file` | Remplace un texte dans un fichier existant | *"Dans script.py, remplace 'version=1' par 'version=2'"* |
| `edit_pdf` | **Modifie du texte dans un PDF en gardant la mise en page** | *"Dans recu.pdf, remplace 'Jean Dupont' par 'Mohamed Kaba'"* |
| `get_folder_info` | Statistiques d'un dossier (taille, nombre de fichiers, types) | *"Quelle est la taille de mon dossier Vidéos ?"* |

---

## 2. Documents — 4 outils

Amah crée des documents professionnels prêts à l'emploi.

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `create_word` | Crée un document Word (.docx) mis en forme | *"Crée un CV pour Mohamed Kaba ingénieur"* |
| `create_pdf` | Crée un fichier PDF | *"Génère une facture PDF pour le client Dupont"* |
| `create_txt` | Crée un fichier texte brut | *"Crée un fichier todo.txt avec ma liste de tâches"* |
| `read_document` | Lit le contenu d'un Word ou PDF | *"Lis-moi le contrat.docx"* |

---

## 3. Internet et Navigation — 7 outils

Amah peut naviguer sur le web, lire des pages, remplir des formulaires.

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `web_search` | Recherche sur DuckDuckGo (sans tracking) | *"Cherche le cours du Bitcoin aujourd'hui"* |
| `read_webpage` | Lit le texte d'une page web depuis son URL | *"Lis-moi cet article : [url]"* |
| `open_browser` | Ouvre une URL dans Chrome | *"Ouvre youtube.com"* |
| `click_element` | Clique sur un bouton ou lien de la page | *"Clique sur le bouton Connexion"* |
| `fill_form` | Remplit un champ de formulaire | *"Entre 'Paris' dans le champ de recherche"* |
| `take_screenshot` | Capture l'écran du navigateur | *"Prends une capture de cette page"* |
| `get_page_text` | Extrait tout le texte de la page ouverte | *"Lis-moi ce qui est écrit sur cette page"* |

---

## 4. Email Gmail — 3 outils

Amah lit et envoie des emails depuis le compte Gmail configuré.

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `read_emails` | Lit les N derniers emails (expéditeur, sujet, extrait) | *"Lis mes 5 derniers emails"* |
| `send_email` | Envoie un email | *"Envoie un email à paul@gmail.com, sujet Réunion, corps : Bonjour…"* |
| `search_emails` | Cherche dans la boîte Gmail | *"Cherche les emails de Google"* |

> Amah demande toujours confirmation avant d'envoyer un email.

---

## 5. Système Windows — 5 outils

Amah surveille et contrôle ton PC.

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `get_system_info` | RAM, CPU, tous les disques, version Windows | *"Comment va mon PC ?"* |
| `open_file` | Ouvre un fichier ou dossier avec le programme par défaut | *"Ouvre le fichier rapport.pdf"* |
| `run_command` | Exécute une commande PowerShell (sécurisée) | *"Liste les processus qui consomment le plus de CPU"* |
| `list_processes` | Affiche les processus actifs triés par utilisation CPU | *"Qu'est-ce qui ralentit mon PC ?"* |
| `get_network_info` | Adresse IP locale et test de connexion internet | *"Quelle est mon adresse IP ?"* |

---

## 6. Contrôle Hardware — 6 outils *(nouveau v1.4)*

Amah contrôle directement le son, la luminosité et le WiFi.

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `set_volume` | Règle le volume système (0–100) | *"Règle le volume à 50%"* |
| `get_audio_level` | Retourne le volume actuel | *"Quel est le volume actuel ?"* |
| `mute_audio` | Active / désactive le silence | *"Mets en muet"* |
| `set_brightness` | Règle la luminosité de l'écran (0–100) | *"Baisse la luminosité à 30%"* |
| `get_brightness` | Retourne la luminosité actuelle | *"Quelle est la luminosité ?"* |
| `wifi_toggle` | Active ou désactive le WiFi | *"Désactive le WiFi"* |

---

## 7. Vision IA — 1 outil *(nouveau v1.4)*

Amah peut voir et analyser ton écran grâce à l'IA vision de Groq.

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `analyze_screen` | Capture l'écran et l'analyse par IA | *"Qu'est-ce que tu vois sur mon écran ?"* |
| | | *"Explique-moi ce graphique"* |
| | | *"Y a-t-il des erreurs affichées ?"* |

---

## 8. YouTube — 2 outils *(nouveau v1.4)*

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `open_youtube` | Ouvre YouTube avec une recherche dans Chrome | *"Mets une musique relaxante sur YouTube"* |
| `search_youtube` | Cherche des vidéos YouTube sans ouvrir le navigateur | *"Cherche des tutoriels Python sur YouTube"* |

---

## 9. Vols et Voyages — 1 outil *(nouveau v1.4)*

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `search_flights` | Recherche des vols et ouvre Google Flights | *"Cherche des vols Paris → Dakar le 15 juillet"* |

---

## 10. Mémoire Persistante — 3 outils

Amah se souvient d'informations entre les sessions.

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `save_memory` | Mémorise une information | *"Souviens-toi que mon médecin s'appelle Dr. Martin"* |
| `get_memories` | Rappelle les infos mémorisées | *"Qu'est-ce que tu sais sur moi ?"* |
| `delete_memory` | Supprime une mémoire | *"Oublie l'info numéro 3"* |

> Les mémoires survivent entre les redémarrages d'Amah (base SQLite locale).

---

## 11. Voix et Interface Plein Écran — 3 outils + 2 interfaces

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `speak` | Lit un texte à voix haute | *"Dis-moi la météo à voix haute"* |
| `listen` | Écoute le microphone et transcrit | *"Écoute ce que je dis"* |
| `listen_continuous` | Écoute pendant X secondes | *"Enregistre ce que je dis pendant 30 secondes"* |

**Interface Vocale Plein Écran** (`◉ Mode Voix` dans l'en-tête) :
- HUD futuriste style Amah — hexagone rotatif cyan, radar animé, barres audio
- Parle → Amah répond à voix haute — en boucle complète

**Mode Réveil — "Amah écoute"** (`⬡ Amah écoute` dans l'en-tête) :
- Tourne silencieusement en arrière-plan
- Widget hexagone dans le coin bas-droit de l'écran
- **Dis simplement "Amah"** → l'interface plein écran apparaît automatiquement
- Clic droit sur le widget → menu (ouvrir / quitter)
- Déplaçable par glisser-déposer

---

## 12. Notifications et Rappels — 2 outils

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `send_notification` | Affiche une notification Windows | *"Notifie-moi : réunion dans 5 minutes"* |
| `set_reminder` | Programme un rappel dans X minutes | *"Rappelle-moi d'appeler Jean dans 20 minutes"* |

---

## 13. Excel — 3 outils

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `read_excel` | Lit un fichier Excel | *"Lis le fichier budget.xlsx"* |
| `create_excel` | Crée un fichier Excel avec en-têtes et données | *"Crée un tableau Excel avec Nom, Prénom, Email"* |
| `append_to_excel` | Ajoute des lignes à un Excel existant | *"Ajoute Mohamed Kaba dans le fichier clients.xlsx"* |

---

## 14. Utilitaires — 10 outils

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `calculate` | Calcule une expression | *"Calcule 15% de 250"* |
| `get_datetime` | Date et heure actuelles | *"Quelle heure est-il ?"* |
| `add_days` | Date dans X jours | *"Dans combien de jours c'est le 25 décembre ?"* |
| `generate_password` | Génère un mot de passe sécurisé | *"Génère un mot de passe de 20 caractères"* |
| `convert_units` | Convertit des unités | *"Convertis 100 km/h en mph"* |
| `zip_files` | Compresse des fichiers en ZIP | *"Compresse ces 3 fichiers en archive.zip"* |
| `unzip_file` | Extrait un fichier ZIP | *"Extrais le fichier archive.zip"* |
| `list_archive` | Affiche le contenu d'un ZIP | *"Qu'est-ce qu'il y a dans ce ZIP ?"* |
| `read_clipboard` | Lit le presse-papiers | *"Qu'est-ce que j'ai copié ?"* |
| `write_clipboard` | Copie un texte dans le presse-papiers | *"Copie ce texte dans le presse-papiers"* |

---

## 15. Images — 4 outils

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `screenshot_full` | Capture l'écran entier du PC | *"Capture mon écran"* |
| `resize_image` | Redimensionne une image | *"Réduis cette image à 800x600 pixels"* |
| `get_image_info` | Dimensions, format, taille d'une image | *"Infos sur cette photo"* |
| `convert_image` | Convertit vers PNG, JPEG, WEBP, BMP | *"Convertis cette image en PNG"* |

---

## 16. Météo — 2 outils

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `get_weather` | Météo complète + prévisions 3 jours | *"Météo à Paris pour cette semaine"* |
| `get_weather_simple` | Météo en une ligne courte | *"Il fait combien à Dakar ?"* |

---

## 17. Traduction — 2 outils

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `translate` | Traduit vers n'importe quelle langue | *"Traduis ce texte en anglais"* |
| `detect_language` | Détecte la langue d'un texte | *"Dans quelle langue est ce texte ?"* |

---

## 18. QR Code — 1 outil

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `create_qrcode` | Génère un QR code depuis un texte ou URL | *"Crée un QR code pour mon site web"* |

---

## 19. Planificateur Windows — 4 outils

Les tâches s'exécutent même quand Amah est fermée.

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `create_daily_task` | Crée une tâche quotidienne Windows | *"Exécute ce script chaque jour à 8h"* |
| `list_tasks` | Liste les tâches planifiées par Amah | *"Quelles tâches as-tu planifiées ?"* |
| `delete_task` | Supprime une tâche planifiée | *"Supprime la tâche backup"* |
| `run_task_now` | Lance une tâche immédiatement | *"Lance la tâche rapport maintenant"* |

---

## 20. Planification IA — 1 outil *(nouveau v1.4)*

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `create_plan` | Génère un plan multi-étapes pour une tâche complexe | *"Planifie comment créer et envoyer mon rapport mensuel"* |

---

## 21. Statistiques et Système Amah — 5 outils

| Outil | Ce qu'il fait | Exemple |
|---|---|---|
| `get_stats` | Statistiques d'utilisation des outils (30 derniers jours) | *"Quels outils utilises-tu le plus ?"* |
| `reset_stats` | Efface les statistiques | *"Réinitialise les stats"* |
| `check_update` | Vérifie si une mise à jour est disponible | *"Y a-t-il une nouvelle version d'Amah ?"* |
| `get_current_version` | Retourne la version installée | *"Quelle version es-tu ?"* |
| `get_license_info` | Informations de licence de cette installation | *"Infos sur ma licence"* |

---

## Limites à connaître

| Limite | Détail |
|---|---|
| **PDF complexes** | `edit_pdf` peut modifier du texte simple. Les PDFs avec champs de formulaire interactifs ou texte vectoriel peuvent résister. |
| **Tokens Groq** | ~3 000 tokens par échange après optimisation. ~7 000 échanges/jour sur compte gratuit. |
| **Reconnaissance vocale** | Nécessite un micro. Fonctionne hors ligne via Windows Speech API. |
| **Navigateur** | Nécessite Chromium installé via `installer_navigateur.bat`. |
| **WiFi toggle** | Nécessite les droits administrateur sur certains PC. |
| **Luminosité** | Fonctionne sur écrans intégrés (laptop). Peut ne pas fonctionner sur certains moniteurs externes. |

---

## Résumé chiffré

| Catégorie | Nombre d'outils |
|---|---|
| Fichiers et dossiers | 10 |
| Documents (Word, PDF, TXT) | 4 |
| Internet et navigation | 7 |
| Email Gmail | 3 |
| Système Windows | 5 |
| Hardware (volume, luminosité, WiFi) | 6 |
| Vision IA (analyse d'écran) | 1 |
| YouTube | 2 |
| Vols et voyages | 1 |
| Mémoire persistante | 3 |
| Voix | 3 |
| Notifications et rappels | 2 |
| Excel | 3 |
| Utilitaires (calcul, zip, presse-papiers…) | 10 |
| Images | 4 |
| Météo | 2 |
| Traduction | 2 |
| QR Code | 1 |
| Planificateur Windows | 4 |
| Planification IA | 1 |
| Statistiques et système Amah | 5 |
| **TOTAL** | **79** |

---

*Amah Agent v1.4.1 — contact.amah.officiel@gmail.com*
