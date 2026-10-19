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

# 3 bis. Ce qui est dit = ce qui est affiché : coupé à la fin d'une phrase
from tools.conversation import spoken_excerpt
long_reply = " ".join(f"Phrase {i} de la réponse, qui continue un peu." for i in range(15))
excerpt, was_cut = spoken_excerpt(long_reply)
check("réponse longue : coupée à la fin d'une phrase (jamais au milieu)",
      was_cut and excerpt.endswith(".") and len(excerpt) <= 450)
check("réponse courte : dite et affichée en entier, sans Markdown",
      spoken_excerpt("Il est **21 h**.") == ("Il est 21 h.", False))

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

# 7. Mots déformés par la reconnaissance vocale (journal du 18-19/10/2026)
from tools.conversation import fix_transcript, today_line
fixes = {
    "récupère tous mes projets sur jet top": "récupère tous mes projets sur GitHub",
    "active le chaîne de test": "active le champ de texte",
    "à moi tu peux me dire il fait quelle heure": "Amah, tu peux me dire il fait quelle heure",
    "ama": "Amah",
}
check("transcriptions corrigées (jet top -> GitHub, chaîne de test -> champ de texte, à moi -> Amah)",
      all(fix_transcript(k) == v for k, v in fixes.items()))
check("phrases normales intactes (Emma Watson, un chat, YouTube)",
      all(fix_transcript(t) == t for t in ("Emma Watson est une actrice", "j'ai un chat à la maison",
                                            "tu peux ouvrir YouTube")))
github_heard = {
    "tu peux me lister tous mes projets sur YouTube": "tu peux me lister tous mes projets sur GitHub",
    "récupère le code sur YouTube": "récupère le code sur GitHub",
    "montre mes dépôts YouTube": "montre mes dépôts GitHub",
}
check("« YouTube » pour des projets ou du code -> GitHub (mal entendu par Google)",
      all(fix_transcript(k) == v for k, v in github_heard.items()))
check("vrai YouTube intact (ouvre YouTube, musique, vidéo de mon projet)",
      all(fix_transcript(t) == t for t in ("ouvre YouTube", "mets de la musique sur YouTube",
                                            "la vidéo de mon projet sur YouTube", "cherche des tutos sur YouTube")))
check("date du jour fournie au modèle (année en cours)", str(__import__("datetime").date.today().year) in today_line())

# 8. Mode Live avec Henri : le découpage en phrases ne perd jamais de texte
import tools.voice as voice_module
splitter = object.__new__(voice_module.SentenceSpeaker)
splitter._buffer, splitter.MAX_PENDING, spoken_parts = "", 180, []
splitter._say = spoken_parts.append
reply = "Ton site est https://campusmarket-nu.vercel.app. Il fait 3.5 degrés. "
for i in range(0, len(reply), 5):
    splitter.feed(reply[i:i + 5])
check("découpage du mode Live : adresse web gardée dans sa phrase, rien de perdu",
      "".join(spoken_parts) + splitter._buffer == reply and "vercel.app." in spoken_parts[0])

# 9. Fin des boucles d'outils : après MAX_TOOL_ROUNDS tours, une réponse sans outil
from types import SimpleNamespace
import tools.conversation as conversation_module
from tools.conversation import MAX_TOOL_ROUNDS, WRAP_UP_FALLBACK, wrap_up
conversation_module.log_error = lambda context, exc: None    # pas d'écriture dans amah_errors.log
sent = []


def fake_model(messages):
    sent.append(messages)
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Voici ce que j'ai trouvé."))])


def failing_model(messages):
    raise RuntimeError("tool_use_failed")


history = [{"role": "system", "content": "x"},
           {"role": "user", "content": "météo"},
           {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "get_weather", "arguments": "{}"}}]},
           {"role": "tool", "content": "27 °C"}, {"role": "assistant", "content": "Il fait 27 °C."},
           {"role": "user", "content": "liste mes projets"},
           {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "web_search", "arguments": '{"query": "projets"}'}}]},
           {"role": "tool", "content": "aucun résultat"}]
check(f"boucle d'outils : {MAX_TOOL_ROUNDS} tours au plus, puis réponse du modèle sans outil",
      2 <= MAX_TOOL_ROUNDS <= 6 and wrap_up(fake_model, history).choices[0].message.content == "Voici ce que j'ai trouvé."
      and len(history) == 8)
check("réponse finale : plus aucun message d'outil, résultats de la demande en cours en texte",
      not any(m.get("role") == "tool" or m.get("tool_calls") for m in sent[0])
      and "web_search" in sent[0][-1]["content"] and "aucun résultat" in sent[0][-1]["content"]
      and "get_weather" not in sent[0][-1]["content"] and sent[0][-2]["content"] == "liste mes projets")
check("boucle d'outils : si la dernière réponse échoue, message d'excuse (pas d'erreur)",
      wrap_up(failing_model, history).choices[0].message.content == WRAP_UP_FALLBACK)

# 10. Session vocale du 19/10/2026 (formulaire de CampusMarket)
dictated = {
    "il y a une chambre de contact tu peux mettre mon numéro": "il y a une champ de contact tu peux mettre mon numéro",
    "il y a un chat mail aussi": "il y a un champ mail aussi",
    "les projets que tu vois dans mon compte du top": "les projets que tu vois dans mon compte GitHub",
}
check("« chambre de contact », « chat mail », « compte du top » corrigés",
      all(fix_transcript(k) == v for k, v in dictated.items()))
check("« chambre d'hôtel », « mon chat », « c'est du top » intacts",
      all(fix_transcript(t) == t for t in ("réserve une chambre de luxe", "mon chat dort", "c'est du top")))

from tools.conversation import drop_old_tool_results, with_recent_tools


def request(text, tool, result, reply):
    return [{"role": "user", "content": text},
            {"role": "assistant", "content": "", "tool_calls": [{"id": text, "function": {"name": tool, "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": text, "content": result},
            {"role": "assistant", "content": reply}]


session = ([{"role": "system", "content": "x"}]
           + request("ouvre campus market", "open_browser", "page " * 500, "C'est ouvert.")
           + request("clique sur devenir vendeur", "click_text", "ok", "J'ai cliqué.")
           + request("remplis le formulaire", "type_in_field", "ok", "C'est rempli.")
           + [{"role": "user", "content": "il y a un champ de contact"}])
light = drop_old_tool_results(session)
check("historique allégé : résultats d'outils des demandes anciennes retirés, réponses gardées",
      len(str(light)) < len(str(session)) / 3 and "C'est ouvert." in str(light)
      and not any(m.get("tool_calls") and m["tool_calls"][0]["function"]["name"] in ("open_browser", "click_text")
                  for m in light))
check("historique allégé : demande précédente intacte, aucun résultat orphelin",
      any(m.get("role") == "tool" and m.get("tool_call_id") == "remplis le formulaire" for m in light)
      and all(m.get("role") != "tool" or light[i - 1].get("tool_calls") or light[i - 1].get("role") == "tool"
              for i, m in enumerate(light)))
routed = with_recent_tools([TOOLS_DEFINITIONS[0]], session, TOOLS_DEFINITIONS)
check("suite d'une demande (« il y a un champ de contact ») : outils du navigateur gardés",
      {"type_in_field", "click_text", "get_page_text"} <= {t["function"]["name"] for t in routed})
check("conversation pure : toujours aucun outil", with_recent_tools([], session, TOOLS_DEFINITIONS) == [])

print(f"\n{sum(results)}/{len(results)} vérifications réussies")
sys.exit(0 if all(results) else 1)
