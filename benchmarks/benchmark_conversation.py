"""Vérifie les briques communes aux 3 interfaces (tools/conversation.py) et le
classement des outils du terminal (tools/security_v02.py) — sans appel API.

Lancer depuis la racine du projet :
    py -3.13 -m benchmarks.benchmark_conversation

Code de sortie 1 si une vérification échoue.
"""
import random
import sys

from tools.conversation import clip_tool_result, speech_text, trim_history
from tools.security_v02 import authorize_tool, classify_tool

results = []


def check(label, condition):
    results.append(bool(condition))
    print(("OK    " if condition else "ECHEC ") + label)


# 1. Coupure de l'historique : jamais de résultat d'outil orphelin en tête
def tour(kind):
    m = [{"role": "user"}]
    if kind == "parallele":       # un message assistant, 2 appels -> 2 résultats
        m += [{"role": "assistant", "tool_calls": [1, 2]}, {"role": "tool"}, {"role": "tool"}]
    else:
        for _ in range(kind):
            m += [{"role": "assistant", "tool_calls": [1]}, {"role": "tool"}]
    return m + [{"role": "assistant"}]


random.seed(7)
orphans = 0
for _ in range(500):
    messages = [{"role": "system"}]
    for kind in [random.choice([0, 1, 2, "parallele"]) for _ in range(15)]:
        for m in tour(kind):
            messages.append(m)
            if m["role"] == "user":
                messages = trim_history(messages, 20)
                orphans += messages[1]["role"] == "tool"
check("500 conversations avec appels parallèles : aucun résultat d'outil orphelin", orphans == 0)
short = [{"role": "system"}, {"role": "user"}]
check("historique court : inchangé", trim_history(short, 20) is short)
check("system toujours gardé en tête", trim_history([{"role": "system"}] + [{"role": "user"}] * 40, 20)[0]["role"] == "system")

# 2. Troncature des résultats d'outils
check("page web : 4 000 caractères", len(clip_tool_result("get_page_text", "x" * 9000)) < 4100)
check("nom déformé par gpt-oss reconnu (tool.read_webpage)", len(clip_tool_result("tool.read_webpage", "x" * 9000)) > 3900)
check("autres outils : 2 000 caractères", len(clip_tool_result("read_emails", "x" * 9000)) < 2100)
check("résultat court : inchangé", clip_tool_result("calculate", '{"r": 4}') == '{"r": 4}')

# 3. Texte prononcé sans Markdown
check("gras retiré", speech_text("La version est **3.14.8**.") == "La version est 3.14.8.")
check("titres et puces -> phrases",
      speech_text("### Météo\n- **Conakry** : 27 °C\n- *Ensoleillé*") == "Météo. Conakry : 27 °C. Ensoleillé.")
check("lien -> son texte seul", speech_text("Voir [la doc](https://docs.python.org).") == "Voir la doc.")
check("tableau -> cellules séparées", speech_text("| Ville | Temp |\n|---|---|\n| Conakry | 27 °C |") == "Ville, Temp. Conakry, 27 °C.")
check("calcul avec * conservé", speech_text("3 * 4 = 12") == "3 * 4 = 12.")

# 4. Terminal : mêmes confirmations que le garde-fou central
check("terminal : lire la mémoire, briefing, lecture, traduction sans autorisation",
      all(classify_tool(n, a) == "SAFE" for n, a in [
          ("get_memories", {}), ("morning_briefing", {}), ("read_aloud", {}), ("translate", {"text": "x"})]))
check("terminal : suppression, envoi d'email, programme .exe -> autorisation",
      all(classify_tool(n, a) == "CONFIRM" for n, a in [
          ("delete_file", {"path": "x"}), ("send_email", {}), ("open_file", {"path": "a.exe"})]))
check("terminal : format C: toujours bloqué",
      authorize_tool("run_command", {"command": "format C:"}).level == "RESTRICTED")

# 5. Compréhension vocale : transcriptions réelles de Google (banc vocal du
#    18/10/2026, voix Henri / Denise / Hortense, avec et sans bruit)
import amah_listener
import voice_fullscreen
from tools.fastpath_v01 import _extract_calculation, normalize_text

listener = object.__new__(amah_listener.ListenerWidget)
check("réveil : « Hama », « ama », « Hama quelle heure est-il » reconnus",
      all(listener._is_wake(t.lower()) for t in ("Hama", "ama", "Hama quelle heure est-il")))
check("réveil : « ami », « amour », « hamac » ignorés",
      not any(listener._is_wake(t) for t in ("ami", "amour", "hamac")))
quit_ok = ["au revoir Amah", "au revoir à ma", "au revoir Emma", "Amah, ferme-toi", "stop", "bonne nuit Amah"]
quit_no = ["arrête la lecture", "ferme Chrome", "arrête la musique", "dis au revoir à Fatou",
           "le magasin ferme à quelle heure ?", "stop le minuteur"]
check("voix : « au revoir à ma », « ferme-toi », « stop »… ferment l'interface",
      all(voice_fullscreen._is_quit_request(t) for t in quit_ok))
check("voix : « arrête la lecture », « ferme Chrome »… ne la ferment plus",
      not any(voice_fullscreen._is_quit_request(t) for t in quit_no))
calc = {"combien font 12 x 15": "12*15", "combien fait 12 fois 15": "12*15", "12 x 15": "12*15",
        "combien font 100 divisé par 4": "100/4"}
check("calcul dicté (« combien font 12 x 15 »…) : réponse instantanée",
      all(_extract_calculation(normalize_text(t)) == e for t, e in calc.items()))
check("pas de calcul pour « 30 », « 18/10/2026 », un numéro de téléphone",
      not any(_extract_calculation(normalize_text(t)) for t in ("30", "18/10/2026", "2026-10-18", "+224 611 76 85 52")))

# 6. Voix réelle de l'utilisateur (test du 18/10/2026) : Google écrit "Amah"
#    "à moi", "ahma", "am" ; "lis-moi la météo" n'est pas une lecture de page
from config import TOOLS_DEFINITIONS
from tools.instant import _STOP_READING
from tools.tool_router import select_tools

check("réveil : « am » en premier mot, « ahma » reconnus ; « am » en fin de phrase ignoré",
      listener._is_wake("am") and listener._is_wake("ahma tu peux me dire")
      and not listener._is_wake("je suis là am"))
check("arrêt de lecture : « arrête à moi », « à moi stop », « stop Amah »",
      all(_STOP_READING.match(t) for t in ("arrête à moi", "à moi stop", "stop Amah", "ama arrête")))
check("arrêt de lecture : « stoppe alarme », « arrête le PC » ne sont pas des arrêts",
      not any(_STOP_READING.match(t) for t in ("stoppe alarme", "arrête le PC")))
check("« lis-moi la météo », « lis-moi mes emails » : pas de lecture de page web",
      not any("read_aloud" in [x["function"]["name"] for x in select_tools(t, TOOLS_DEFINITIONS)[0]]
              for t in ("lis-moi la météo de Paris", "lis-moi mes emails")))

print(f"\n{sum(results)}/{len(results)} vérifications réussies")
sys.exit(0 if all(results) else 1)
