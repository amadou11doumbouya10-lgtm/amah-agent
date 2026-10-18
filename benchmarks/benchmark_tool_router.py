"""Benchmark du routeur partagé (tools/tool_router.py) — sans appel API.

Lancer depuis la racine du projet :
    py -3.13 -m benchmarks.benchmark_tool_router

AUDIT40 : demandes de l'audit du 14/10/2026. HELDOUT : phrases écrites AVANT le
routeur, formulées autrement que ses mots-clés. N'ajoute pas un mot-clé au
routeur juste pour faire passer une phrase de HELDOUT : ce jeu mesure la
compréhension de formulations nouvelles, pas la mémorisation (les anciens
benchmarks du routeur reprenaient les phrases des motifs).
Valeur attendue : noms d'outils acceptés séparés par |, "" = conversation pure.
Code de sortie 1 si une demande est mal routée.
"""
import sys

from config import TOOLS_DEFINITIONS
from tools.tool_router import select_tools

AUDIT40 = {
 'lis mes 3 derniers emails':'read_emails','envoie un email à paul@test.com pour dire bonjour':'send_email',
 'mémorise que ma couleur préférée est le vert':'save_memory',"qu est-ce que tu as en mémoire sur moi ?":'get_memories',
 'écris un script python qui affiche bonjour':'write_file|write_code','mets le volume à 30':'set_volume','coupe le son':'mute_audio',
 'baisse la luminosité à 40':'set_brightness','désactive le wifi':'wifi_toggle','mets une vidéo YouTube de Didi B':'open_youtube|play_music',
 'joue de la musique de Burna Boy':'play_music','ouvre Steam':'open_steam','lance le jeu Counter Strike':'launch_game_steam',
 'crée un QR code pour https://example.com':'create_qrcode','crée un document Word avec un rapport':'create_word','crée un PDF de mon CV':'create_pdf',
 'lis le fichier C:/x/notes.txt':'read_file','crée un tableau Excel des dépenses':'create_excel','traduis bonjour en anglais':'translate',
 'quel temps fait-il à Dakar ?':'get_weather_simple|get_weather',"rappelle-moi dans 10 minutes de boire de l eau":'set_reminder',
 'zippe le dossier projets':'zip_files','décompresse archive.zip':'unzip_file','trouve un vol Paris Conakry':'search_flights',
 'quels processus consomment le plus ?':'list_processes','donne-moi les infos de mon système':'get_system_info','ferme chrome':'kill_process',
 'ouvre google.com':'open_browser','range mon dossier téléchargements':'organize_folder','crée une tâche planifiée tous les jours à 8h':'create_daily_task',
 'regarde-moi avec la webcam':'analyze_webcam',"copie ce texte dans le presse-papiers : salut":'write_clipboard','génère un mot de passe':'generate_password',
 'quelle est ma licence ?':'get_license_info','y a-t-il une mise à jour ?':'check_update',"redimensionne l image photo.png en 200x200":'resize_image',
 'exécute le script C:/x/test.py':'run_code','organise mes tâches pour préparer un voyage':'create_plan|execute_plan',
 "montre-moi mes statistiques d utilisation":'get_stats','écoute-moi':'listen',
}

HELDOUT = {
 "tu peux me montrer mes derniers mails ?": "read_emails",
 "écris un mail à fatou@exemple.com pour lui souhaiter bon anniversaire": "send_email|draft_email",
 "note bien que je préfère le thé au café": "save_memory",
 "qu'est-ce que tu sais sur moi ?": "get_memories",
 "fais-moi une page html avec un bouton rouge dans C:/site/index.html": "write_file|write_code",
 "monte un peu le son": "set_volume",
 "mets-moi en sourdine": "mute_audio",
 "l'écran est trop lumineux, baisse-le": "set_brightness",
 "rallume le wifi": "wifi_toggle",
 "trouve-moi un clip de Sidiki Diabaté sur YouTube": "open_youtube|search_youtube|play_music",
 "je veux écouter du Wizkid": "play_music|open_youtube",
 "démarre Fortnite": "launch_game_steam|open_epic_games",
 "génère un QR code avec mon numéro de téléphone": "create_qrcode",
 "rédige une lettre de motivation au format Word": "create_word",
 "convertis ce texte en PDF : bonjour": "create_pdf",
 "ouvre le contenu de C:/notes/todo.txt": "read_file",
 "fais un tableau excel avec mes dépenses du mois": "create_excel",
 "comment on dit merci en wolof ?": "translate",
 "il va faire beau à Kankan demain ?": "get_weather|get_weather_simple",
 "préviens-moi dans 20 minutes pour le rendez-vous": "set_reminder",
 "compresse le dossier C:/projets en zip": "zip_files",
 "extrais l'archive C:/tmp/photos.zip": "unzip_file",
 "je cherche un billet d'avion pour Abidjan": "search_flights",
 "pourquoi mon pc rame ? montre ce qui consomme le plus": "list_processes",
 "combien de RAM a mon ordinateur ?": "get_system_info",
 "arrête le processus notepad": "kill_process",
 "va sur le site de la BBC": "open_browser",
 "trie les fichiers de mon dossier Téléchargements": "organize_folder",
 "programme une tâche chaque matin à 7h pour lancer la sauvegarde": "create_daily_task",
 "qu'est-ce que tu vois avec la caméra ?": "analyze_webcam",
 "colle dans le presse-papiers le mot bonjour": "write_clipboard",
 "il me faut un mot de passe solide de 20 caractères": "generate_password",
 "ma clé de licence est-elle valide ?": "get_license_info",
 "est-ce qu'une nouvelle version d'Amah est disponible ?": "check_update",
 "réduis la taille de la photo C:/img/vacances.jpg à 800 pixels": "resize_image",
 "lance le programme python C:/scripts/backup.py": "run_code",
 "prépare et exécute un plan pour organiser mon anniversaire": "create_plan|execute_plan",
 "combien de fois j'ai utilisé chaque outil ?": "get_stats",
 "c'est combien 15% de 2400 ?": "calculate",
 "on est quel jour aujourd'hui ?": "get_datetime",
 "que vois-tu sur mon écran ?": "analyze_screen",
 "lis-moi ce PDF : C:/docs/contrat.pdf": "read_document|read_file|summarize",
 "résume le document C:/docs/rapport.docx": "summarize|read_document",
 "fais une capture de mon écran": "screenshot_full|take_screenshot",
 "quelle est mon adresse IP ?": "get_network_info",
 # conversation pure : aucun outil attendu
 "salut Amah": "",
 "merci beaucoup !": "",
 "bonsoir, comment tu vas ?": "",
 "ok super merci": "",
 "qu'est-ce que tu sais faire ?": "",
 # salutation + vraie demande
 "bonjour, lis mes emails": "read_emails",
 "salut, quel temps fait-il à Labé ?": "get_weather|get_weather_simple",
 "merci, maintenant mets le volume à 50": "set_volume",
 "hey Amah, ouvre Steam": "open_steam",
 "est-ce que ça va pleuvoir à Conakry ?": "get_weather|get_weather_simple",
}

# Phrases ratées lors de vrais essais : les mots "version" et "prix" envoyaient
# la question vers code/amah ou utils, sans web_search (test du 18/10/2026).
REGRESSIONS = {
 "quelle est la dernière version de Python sortie ?": "web_search",
 "quel est le prix du bitcoin aujourd'hui": "web_search",
 "les nouveautés de Windows 11": "web_search",
 # "lis" déclenchait aussi les outils fichiers : read_aloud sortait des 12
 "lis-moi l'article https://fr.wikipedia.org/wiki/Conakry": "read_aloud",
 "peux-tu me lire la page ouverte": "read_aloud",
 "arrête la lecture": "read_aloud",
}


def score(cases):
    ok, misses, sizes = 0, [], []
    for question, expected in cases.items():
        tools, _info = select_tools(question, TOOLS_DEFINITIONS)
        names = [t["function"]["name"] for t in tools]
        if expected == "":
            hit = not names
        else:
            hit = any(e in names for e in expected.split("|"))
            sizes.append(len(names))
        ok += hit
        if not hit:
            misses.append((question, expected, names[:6]))
    return ok, misses, (sum(sizes) / len(sizes) if sizes else 0)


if __name__ == "__main__":
    failed = False
    for label, cases in (("audit", AUDIT40), ("nouvelles phrases", HELDOUT),
                         ("régressions", REGRESSIONS)):
        ok, misses, avg = score(cases)
        print(f"{label:18} {ok}/{len(cases)} ({100 * ok / len(cases):.0f} %)  "
              f"outils proposés en moyenne : {avg:.1f}")
        for question, expected, got in misses:
            print(f"    RATÉ {question!r} : attendu {expected}, reçu {got}")
        failed |= bool(misses)
    sys.exit(1 if failed else 0)
