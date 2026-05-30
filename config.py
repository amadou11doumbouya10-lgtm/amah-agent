import os
from pathlib import Path

MODEL = "llama-3.3-70b-versatile"

# Chemins réels de l'utilisateur — injectés dans le prompt pour éviter que le modèle invente des chemins
_HOME      = str(Path.home()).replace("\\", "/")
_DESKTOP   = str(Path.home() / "Desktop").replace("\\", "/")
_DOCUMENTS = str(Path.home() / "Documents").replace("\\", "/")
_DOWNLOADS = str(Path.home() / "Downloads").replace("\\", "/")

SYSTEM_PROMPT = f"""Tu es Amah — assistante IA locale, précise et efficace. Tu parles français.

PC : Bureau={_DESKTOP} | Documents={_DOCUMENTS} | Téléchargements={_DOWNLOADS}

RÈGLE : Appelle TOUJOURS un outil pour agir. Ne réponds jamais par du texte seul.
Fichiers→list_files/organize_folder/find_files/move_file/create_folder/read_file
Docs→create_word/create_pdf/create_txt/read_document
Web→web_search/read_webpage/open_browser/click_element/fill_form/get_page_text
Système→get_system_info/open_file/run_command/list_processes/get_network_info
Mémoire→save_memory/get_memories/delete_memory
Email→read_emails/send_email/search_emails (adresse: contact.amah.officiel@gmail.com)
Voix→speak/listen | Notifications→send_notification/set_reminder
Excel→read_excel/create_excel/append_to_excel
Utilitaires→calculate/get_datetime/add_days/generate_password/convert_units
Archives→zip_files/unzip_file | Images→screenshot_full/resize_image/convert_image
Météo→get_weather_simple/get_weather | Traduction→translate/detect_language
QR→create_qrcode | Planificateur→create_daily_task/list_tasks/delete_task
Stats→get_stats | Mise à jour→check_update | Licence→get_license_info

Règles clés :
- Email : confirme toujours destinataire/sujet avant d'envoyer
- Navigateur : après open_browser, utilise get_page_text pour lire
- Date/heure : appelle get_datetime si besoin
- Tâches complexes : décompose en étapes, appelle les outils dans l'ordre

Après chaque outil : résume en 1-2 phrases claires."""

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Liste les fichiers et dossiers dans un répertoire",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du dossier (ex: C:/Users/moi/Desktop)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "organize_folder",
            "description": "Classe automatiquement les fichiers d'un dossier par type (Images, Vidéos, Documents, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du dossier à organiser"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Cherche des fichiers par nom ou extension dans un dossier",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "Dossier de recherche"},
                    "pattern": {"type": "string", "description": "Motif de recherche (ex: *.pdf, facture*, rapport)"}
                },
                "required": ["path", "pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Déplace ou renomme un fichier",
            "parameters": {
                "type": "object",
                "properties": {
                    "source":      {"type": "string", "description": "Chemin complet du fichier source"},
                    "destination": {"type": "string", "description": "Chemin complet de destination"}
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Crée un nouveau dossier",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin complet du dossier à créer"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lit le contenu d'un fichier texte (TXT, MD, CSV, JSON, PY, HTML...)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin complet du fichier"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_folder_info",
            "description": "Donne des statistiques sur un dossier : taille, nombre de fichiers, types présents",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du dossier"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_word",
            "description": "Crée un document Word (.docx) avec le contenu fourni",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Nom du fichier sans extension"},
                    "title":    {"type": "string", "description": "Titre du document"},
                    "content":  {"type": "string", "description": "Contenu du document"},
                    "save_path":{"type": "string", "description": "Dossier où sauvegarder (défaut: Documents)"}
                },
                "required": ["filename", "title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_txt",
            "description": "Crée un fichier texte (.txt) avec le contenu fourni",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename":  {"type": "string", "description": "Nom du fichier sans extension"},
                    "content":   {"type": "string", "description": "Contenu du fichier"},
                    "save_path": {"type": "string", "description": "Dossier où sauvegarder (défaut: Documents)"}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_pdf",
            "description": "Crée un document PDF avec le contenu fourni",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename":  {"type": "string", "description": "Nom du fichier sans extension"},
                    "title":     {"type": "string", "description": "Titre du document"},
                    "content":   {"type": "string", "description": "Contenu du document"},
                    "save_path": {"type": "string", "description": "Dossier où sauvegarder (défaut: Documents)"}
                },
                "required": ["filename", "title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_document",
            "description": "Lit et retourne le contenu d'un document Word (.docx) ou PDF",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin complet du document"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Effectue une recherche sur internet via DuckDuckGo et retourne les résultats",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":       {"type": "string", "description": "La requête de recherche"},
                    "num_results": {"type": "integer", "description": "Nombre de résultats (défaut: 5)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_webpage",
            "description": "Lit et extrait le contenu textuel d'une page web depuis son URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "L'URL de la page à lire"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Retourne les informations système : RAM utilisée, espace disque, CPU, version Windows. Aucun paramètre requis.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_file",
            "description": "Ouvre un fichier ou dossier avec le programme par défaut de Windows",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier ou dossier à ouvrir"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Exécute une commande PowerShell sûre et retourne le résultat",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "La commande PowerShell à exécuter"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Sauvegarde une information importante en mémoire persistante (survit entre les sessions)",
            "parameters": {
                "type": "object",
                "properties": {
                    "content":  {"type": "string", "description": "L'information à mémoriser"},
                    "category": {"type": "string", "description": "Catégorie : préférence, tâche, info, projet (défaut: general)"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_memories",
            "description": "Récupère les informations mémorisées lors des sessions précédentes",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filtrer par catégorie (optionnel)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_memory",
            "description": "Supprime une mémoire par son identifiant numérique",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "integer", "description": "L'id de la mémoire à supprimer"}
                },
                "required": ["memory_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_emails",
            "description": "Lit les N derniers emails Gmail (expéditeur, sujet, date, extrait du message)",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "description": "Nombre d'emails à lire (défaut: 5)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Envoie un email via Gmail",
            "parameters": {
                "type": "object",
                "properties": {
                    "to":      {"type": "string", "description": "Adresse email du destinataire"},
                    "subject": {"type": "string", "description": "Sujet de l'email"},
                    "body":    {"type": "string", "description": "Corps du message"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Cherche des emails dans Gmail (ex: 'from:google.com', 'subject:facture', 'is:unread')",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Requête de recherche Gmail"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_browser",
            "description": "Ouvre une page web dans un navigateur Chrome visible",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "L'URL à ouvrir (ex: https://google.com)"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_element",
            "description": "Clique sur un élément de la page web ouverte",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Sélecteur CSS ou texte de l'élément (ex: 'button', '#id', 'text=Connexion')"}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fill_form",
            "description": "Remplit un champ de formulaire dans la page web ouverte",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Sélecteur CSS du champ (ex: 'input[name=email]', '#search')"},
                    "value":    {"type": "string", "description": "Valeur à entrer dans le champ"}
                },
                "required": ["selector", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Capture une image de l'écran du navigateur et la sauvegarde",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin de sauvegarde (optionnel, généré automatiquement si absent)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_text",
            "description": "Lit et retourne le contenu textuel de la page web actuellement ouverte dans le navigateur",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "speak",
            "description": "Lit un texte à voix haute via les haut-parleurs du PC",
            "parameters": {
                "type": "object",
                "properties": {
                    "text":  {"type": "string",  "description": "Le texte à lire à voix haute"},
                    "speed": {"type": "integer", "description": "Vitesse de lecture : -5 (lent) à 5 (rapide), défaut 2"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": "Affiche une notification ballon Windows dans le coin bas droite de l'écran",
            "parameters": {
                "type": "object",
                "properties": {
                    "title":    {"type": "string",  "description": "Titre de la notification"},
                    "message":  {"type": "string",  "description": "Contenu de la notification"},
                    "duration": {"type": "integer", "description": "Durée en secondes (défaut: 5)"}
                },
                "required": ["title", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Programme un rappel automatique dans X minutes — une notification apparaîtra",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string",  "description": "Le texte du rappel"},
                    "minutes": {"type": "integer", "description": "Dans combien de minutes envoyer le rappel"}
                },
                "required": ["message", "minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_excel",
            "description": "Lit un fichier Excel (.xlsx) et retourne son contenu",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin complet du fichier Excel"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_excel",
            "description": "Crée un fichier Excel avec en-têtes et données, mise en forme automatique",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename":  {"type": "string", "description": "Nom du fichier sans extension"},
                    "headers":   {"type": "array",  "items": {"type": "string"}, "description": "Liste des en-têtes de colonnes"},
                    "rows":      {"type": "array",  "items": {"type": "array"},  "description": "Lignes de données (liste de listes)"},
                    "save_path": {"type": "string", "description": "Dossier de sauvegarde (défaut: Documents)"}
                },
                "required": ["filename", "headers", "rows"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "append_to_excel",
            "description": "Ajoute des lignes à la fin d'un fichier Excel existant",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin complet du fichier Excel"},
                    "rows": {"type": "array",  "items": {"type": "array"}, "description": "Lignes à ajouter"}
                },
                "required": ["path", "rows"]
            }
        }
    },
    {"type":"function","function":{"name":"read_clipboard","description":"Lit le contenu du presse-papiers Windows","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"write_clipboard","description":"Copie un texte dans le presse-papiers Windows","parameters":{"type":"object","properties":{"text":{"type":"string","description":"Texte a copier"}},"required":["text"]}}},
    {"type":"function","function":{"name":"calculate","description":"Calcule une expression mathematique. Ex: '15% de 250', '(120+80)*1.2'","parameters":{"type":"object","properties":{"expression":{"type":"string","description":"L'expression a calculer"}},"required":["expression"]}}},
    {"type":"function","function":{"name":"get_datetime","description":"Retourne la date, l'heure et le jour de la semaine actuels","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"add_days","description":"Calcule la date dans X jours (negatif = passe)","parameters":{"type":"object","properties":{"days":{"type":"integer","description":"Nombre de jours"}},"required":["days"]}}},
    {"type":"function","function":{"name":"generate_password","description":"Genere un mot de passe securise aleatoire","parameters":{"type":"object","properties":{"length":{"type":"integer","description":"Longueur (defaut 16)"},"include_symbols":{"type":"boolean","description":"Inclure symboles"}},"required":[]}}},
    {"type":"function","function":{"name":"convert_units","description":"Convertit une valeur d'une unite a une autre (km/miles, kg/lbs, Celsius/Fahrenheit...)","parameters":{"type":"object","properties":{"value":{"type":"number","description":"Valeur"},"from_unit":{"type":"string","description":"Unite source"},"to_unit":{"type":"string","description":"Unite cible"}},"required":["value","from_unit","to_unit"]}}},
    {"type":"function","function":{"name":"zip_files","description":"Compresse des fichiers en archive ZIP","parameters":{"type":"object","properties":{"files":{"type":"array","items":{"type":"string"},"description":"Chemins a compresser"},"output":{"type":"string","description":"Chemin ZIP sortie"}},"required":["files"]}}},
    {"type":"function","function":{"name":"unzip_file","description":"Extrait un fichier ZIP","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Chemin ZIP"},"destination":{"type":"string","description":"Dossier destination"}},"required":["path"]}}},
    {"type":"function","function":{"name":"list_archive","description":"Liste le contenu d'un ZIP sans l'extraire","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Chemin ZIP"}},"required":["path"]}}},
    {"type":"function","function":{"name":"screenshot_full","description":"Capture l'integralite de l'ecran du PC","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Chemin sauvegarde"}},"required":[]}}},
    {"type":"function","function":{"name":"resize_image","description":"Redimensionne une image","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Chemin image"},"width":{"type":"integer","description":"Largeur pixels"},"height":{"type":"integer","description":"Hauteur pixels"},"output":{"type":"string","description":"Chemin sortie"}},"required":["path"]}}},
    {"type":"function","function":{"name":"get_image_info","description":"Metadonnees d'une image (dimensions, format, taille)","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Chemin image"}},"required":["path"]}}},
    {"type":"function","function":{"name":"convert_image","description":"Convertit une image vers PNG, JPEG, BMP ou WEBP","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Chemin image source"},"to_format":{"type":"string","description":"Format cible"},"output":{"type":"string","description":"Chemin sortie"}},"required":["path","to_format"]}}},
    {"type":"function","function":{"name":"list_processes","description":"Liste les processus Windows actifs tries par CPU","parameters":{"type":"object","properties":{"top":{"type":"integer","description":"Nombre a afficher"}},"required":[]}}},
    {"type":"function","function":{"name":"get_network_info","description":"Adresse IP locale et connectivite internet","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_weather","description":"Meteo complete avec previsions 3 jours pour une ville","parameters":{"type":"object","properties":{"location":{"type":"string","description":"Ville (ex: Paris) ou 'auto' pour geolocalisation"}},"required":[]}}},
    {"type":"function","function":{"name":"get_weather_simple","description":"Meteo en une ligne courte pour une ville","parameters":{"type":"object","properties":{"location":{"type":"string","description":"Ville ou 'auto'"}},"required":[]}}},
    {"type":"function","function":{"name":"translate","description":"Traduit un texte vers n'importe quelle langue","parameters":{"type":"object","properties":{"text":{"type":"string","description":"Texte a traduire"},"to_lang":{"type":"string","description":"Langue cible (fr, en, es, ar, de, it...) ou nom complet (francais, anglais...)"},"from_lang":{"type":"string","description":"Langue source (auto par defaut)"}},"required":["text","to_lang"]}}},
    {"type":"function","function":{"name":"detect_language","description":"Detecte la langue d'un texte","parameters":{"type":"object","properties":{"text":{"type":"string","description":"Texte a analyser"}},"required":["text"]}}},
    {"type":"function","function":{"name":"create_qrcode","description":"Genere un QR code depuis un texte ou une URL","parameters":{"type":"object","properties":{"text":{"type":"string","description":"Texte ou URL a encoder"},"output":{"type":"string","description":"Chemin de sauvegarde (optionnel)"},"size":{"type":"integer","description":"Taille des cases (1-20, defaut 10)"}},"required":["text"]}}},
    {"type":"function","function":{"name":"listen","description":"Ecoute le microphone et retourne le texte reconnu (reconnaissance vocale)","parameters":{"type":"object","properties":{"timeout":{"type":"integer","description":"Duree max d'ecoute en secondes (defaut 5)"},"language":{"type":"string","description":"Code langue (fr-FR, en-US, ar-SA... defaut fr-FR)"}},"required":[]}}},
    {"type":"function","function":{"name":"create_daily_task","description":"Cree une tache planifiee quotidienne dans le Planificateur Windows (s'execute meme quand Amah est fermee)","parameters":{"type":"object","properties":{"name":{"type":"string","description":"Nom unique de la tache"},"command":{"type":"string","description":"Commande PowerShell a executer"},"hour":{"type":"integer","description":"Heure (0-23)"},"minute":{"type":"integer","description":"Minute (0-59)"}},"required":["name","command"]}}},
    {"type":"function","function":{"name":"list_tasks","description":"Liste toutes les taches planifiees Amah","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"delete_task","description":"Supprime une tache planifiee Amah","parameters":{"type":"object","properties":{"name":{"type":"string","description":"Nom de la tache"}},"required":["name"]}}},
    {"type":"function","function":{"name":"get_stats","description":"Statistiques d'utilisation des outils Amah","parameters":{"type":"object","properties":{"days":{"type":"integer","description":"Nombre de jours (defaut 30)"}},"required":[]}}},
    {"type":"function","function":{"name":"check_update","description":"Verifie si une mise a jour d'Amah Agent est disponible","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_current_version","description":"Retourne la version actuelle d'Amah Agent","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_license_info","description":"Affiche les informations de licence de cette installation","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"run_task_now","description":"Lance immediatement une tache planifiee Windows","parameters":{"type":"object","properties":{"name":{"type":"string","description":"Nom de la tache"}},"required":["name"]}}},
    {"type":"function","function":{"name":"reset_stats","description":"Efface toutes les statistiques d'utilisation d'Amah","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"listen_continuous","description":"Ecoute le microphone pendant X secondes et retourne tout ce qui a ete dit","parameters":{"type":"object","properties":{"duration":{"type":"integer","description":"Duree d'ecoute en secondes (defaut 10)"},"language":{"type":"string","description":"Code langue (defaut fr-FR)"}},"required":[]}}}
]
