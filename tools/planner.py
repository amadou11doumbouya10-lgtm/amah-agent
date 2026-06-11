import json
import uuid
import concurrent.futures

from groq_client import GroqClient


_TOOLS_LIST = """web_search, read_webpage, create_word, create_pdf, create_txt, read_document,
send_email, read_emails, search_emails,
list_files, find_files, read_file, write_file, edit_file, create_folder,
get_system_info, run_command, open_file,
calculate, get_datetime, add_days, convert_units,
translate, detect_language,
get_weather, get_weather_simple,
create_excel, read_excel, append_to_excel,
send_notification, set_reminder,
save_memory, get_memories,
open_browser, get_page_text, take_screenshot,
screenshot_full, analyze_screen,
open_youtube, search_youtube,
search_flights,
set_volume, mute_audio, set_brightness, wifi_toggle,
speak, zip_files, create_qrcode"""

_PLAN_SYSTEM = f"""Tu es un planificateur de taches IA. Pour l'objectif donne, genere un plan JSON structure avec des etapes sequentielles.

Format de reponse (JSON uniquement, rien d'autre):
{{
  "objectif": "description courte de l'objectif",
  "etapes": [
    {{"n": 1, "outil": "nom_outil", "desc": "ce que fait cette etape", "params": {{"param1": "valeur1"}}}},
    {{"n": 2, "outil": "nom_outil", "desc": "...", "params": {{...}}}}
  ],
  "note": "remarque ou conseil optionnel"
}}

Outils disponibles:
{_TOOLS_LIST}

Regles strictes:
- Maximum 6 etapes
- Une etape = un seul outil
- Les params doivent etre complets et directs (pas de placeholders comme <valeur>)
- Si l'objectif necessite 1-2 etapes seulement, mets "simple - executer directement" dans note
- Ne cree PAS de plan pour des taches simples (1 outil suffit)"""

_RETRY_SYSTEM = f"""Une etape d'un plan d'action a echoue. Propose UNE etape alternative pour atteindre le
meme but, avec un outil different ou d'autres parametres.

Reponds en JSON uniquement, meme format que l'etape d'origine:
{{"n": <numero>, "outil": "nom_outil", "desc": "...", "params": {{...}}}}

Outils disponibles:
{_TOOLS_LIST}

Regles: un seul outil, params complets et directs (pas de placeholders). Si vraiment aucune alternative
raisonnable n'existe, reponds {{"outil": null}}."""

# Outils sensibles/irreversibles : execute_plan s'arrete et demande confirmation
# avant de les executer (memes outils que la regle ATTENTION du system prompt).
_SENSITIVE_TOOLS = {"run_command", "kill_process", "delete_file", "wifi_toggle", "start_auto_mute", "send_email"}

_STEP_TIMEOUT = 30  # secondes par etape

# Plans en attente de confirmation utilisateur, indexes par plan_id
_PLAN_CACHE = {}


def create_plan(goal: str) -> dict:
    """Genere un plan multi-etapes structure (JSON) pour atteindre un objectif complexe (3+ actions).
    Utilise cet outil pour les taches qui necessitent plusieurs outils en sequence."""
    try:
        client = GroqClient.get()
        resp = client.chat(
            messages=[
                {"role": "system", "content": _PLAN_SYSTEM},
                {"role": "user", "content": f"Objectif: {goal}"},
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            max_tokens=1024,
            temperature=0.2,
        )
        plan = json.loads(resp.choices[0].message.content)
        return {"success": True, **plan}
    except json.JSONDecodeError:
        return {"error": "Plan invalide (JSON malformate)"}
    except RuntimeError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def _run_step_once(tool_name: str, params: dict) -> dict:
    """Execute un outil avec timeout. Retourne toujours un dict (avec "error" si echec)."""
    from tools import TOOL_FUNCTIONS

    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return {"error": f"Outil inconnu: {tool_name}"}

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(lambda: func(**params))
        try:
            result = future.result(timeout=_STEP_TIMEOUT)
        except concurrent.futures.TimeoutError:
            return {"error": f"Timeout depasse ({_STEP_TIMEOUT}s)"}
        except Exception as e:
            return {"error": str(e)}
        return result if isinstance(result, dict) else {"success": True, "resultat": result}
    finally:
        executor.shutdown(wait=False)


def _suggest_alternative(goal: str, step: dict, error: str):
    """Demande a Groq une etape alternative apres l'echec de `step`. Retourne None si aucune."""
    try:
        client = GroqClient.get()
        resp = client.chat(
            messages=[
                {"role": "system", "content": _RETRY_SYSTEM},
                {"role": "user", "content": (
                    f"Objectif global: {goal}\n"
                    f"Etape echouee: {json.dumps(step, ensure_ascii=False)}\n"
                    f"Erreur: {error}"
                )},
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            max_tokens=300,
            temperature=0.3,
        )
        alt = json.loads(resp.choices[0].message.content)
        if alt.get("outil") and isinstance(alt.get("params"), dict):
            return alt
    except Exception:
        pass
    return None


def _brief(result, max_chars=300) -> str:
    """Resume un resultat d'outil pour le rapport (evite de saturer le contexte)."""
    text = json.dumps(result, ensure_ascii=False, default=str) if isinstance(result, (dict, list)) else str(result)
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


def execute_plan(goal: str = None, plan_id: str = None, confirmed: bool = False, on_status=None) -> dict:
    """Genere un plan multi-etapes et l'execute automatiquement (retry si une etape echoue,
    arret + confirmation avant les actions sensibles comme run_command/delete_file/send_email...).
    Pour valider une action en attente, rappelle avec le meme plan_id et confirmed=true."""
    if plan_id:
        state = _PLAN_CACHE.get(plan_id)
        if not state:
            return {"error": f"plan_id inconnu ou expire: {plan_id}"}
        plan, goal, rapport, start = state["plan"], state["goal"], state["rapport"], state["next_step"]
    else:
        if not goal:
            return {"error": "goal requis pour generer un nouveau plan"}
        plan = create_plan(goal)
        if "error" in plan:
            return plan
        if not plan.get("etapes"):
            return {"success": True, "termine": True, "objectif": plan.get("objectif", goal),
                    "rapport": [], "note": plan.get("note", "")}
        plan_id = uuid.uuid4().hex[:8]
        rapport, start = [], 1

    etapes = plan.get("etapes") or []
    total = len(etapes)

    for step in etapes:
        n = step.get("n", 0)
        if n < start:
            continue

        tool_name = step.get("outil")
        desc      = step.get("desc", "")
        params    = step.get("params") or {}

        if on_status:
            on_status(f"Etape {n}/{total} : {desc}...")

        if tool_name in _SENSITIVE_TOOLS and not (confirmed and n == start):
            _PLAN_CACHE[plan_id] = {"plan": plan, "goal": goal, "rapport": rapport, "next_step": n}
            return {
                "success": True, "termine": False, "plan_id": plan_id,
                "objectif": plan.get("objectif", goal), "rapport": rapport,
                "confirmation_requise": {"etape": n, "outil": tool_name, "desc": desc, "params": params},
                "message": (f"Etape {n}/{total} ({tool_name}: {desc}) est une action sensible. "
                            f"Demande confirmation a l'utilisateur, puis si OK rappelle execute_plan "
                            f"avec plan_id=\"{plan_id}\" et confirmed=true."),
            }

        result = _run_step_once(tool_name, params)
        ok = "error" not in result

        if ok:
            rapport.append({"n": n, "outil": tool_name, "desc": desc, "statut": "succes", "resultat": _brief(result)})
            continue

        erreur = result.get("error")
        if on_status:
            on_status(f"Etape {n}/{total} : echec ({erreur}) — recherche d'une alternative...")

        alt = _suggest_alternative(goal, step, erreur)
        if not alt:
            rapport.append({"n": n, "outil": tool_name, "desc": desc, "statut": "echec", "erreur": erreur})
            _PLAN_CACHE.pop(plan_id, None)
            return {"success": True, "termine": True, "objectif": plan.get("objectif", goal),
                    "rapport": rapport, "arret": f"Etape {n}/{total} a echoue ({erreur}) — plan arrete."}

        alt_tool, alt_desc, alt_params = alt.get("outil"), alt.get("desc", desc), alt.get("params") or {}

        if alt_tool in _SENSITIVE_TOOLS:
            # Remplace l'etape en echec par son alternative dans le plan mis en cache,
            # pour qu'a la reprise (confirmed=true) ce soit l'alternative qui s'execute
            # directement -- sans quoi l'etape d'origine, qui echoue toujours, serait
            # rejouee a chaque reprise et redemanderait confirmation indefiniment.
            new_plan = dict(plan)
            new_plan["etapes"] = list(etapes)
            new_plan["etapes"][etapes.index(step)] = {"n": n, "outil": alt_tool, "desc": alt_desc, "params": alt_params}
            _PLAN_CACHE[plan_id] = {"plan": new_plan, "goal": goal, "rapport": rapport, "next_step": n}
            return {
                "success": True, "termine": False, "plan_id": plan_id,
                "objectif": plan.get("objectif", goal), "rapport": rapport,
                "confirmation_requise": {"etape": n, "outil": alt_tool, "desc": alt_desc, "params": alt_params},
                "message": (f"Etape {n}/{total} a echoue ({erreur}). Alternative proposee : "
                            f"{alt_tool} ({alt_desc}), action sensible — demande confirmation a "
                            f"l'utilisateur puis rappelle execute_plan avec plan_id=\"{plan_id}\" et confirmed=true."),
            }

        if on_status:
            on_status(f"Etape {n}/{total} : nouvelle tentative ({alt_desc})...")

        result2 = _run_step_once(alt_tool, alt_params)
        ok2 = "error" not in result2
        rapport.append({
            "n": n, "outil": tool_name, "desc": desc, "statut": "succes" if ok2 else "echec",
            "erreur": erreur,
            "alternative": {"outil": alt_tool, "desc": alt_desc,
                            "resultat": _brief(result2) if ok2 else result2.get("error")},
        })
        if not ok2:
            _PLAN_CACHE.pop(plan_id, None)
            return {"success": True, "termine": True, "objectif": plan.get("objectif", goal),
                    "rapport": rapport, "arret": f"Etape {n}/{total} et son alternative ont echoue — plan arrete."}

    _PLAN_CACHE.pop(plan_id, None)
    return {"success": True, "termine": True, "objectif": plan.get("objectif", goal), "rapport": rapport}
