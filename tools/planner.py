import os
import json


_PLAN_SYSTEM = """Tu es un planificateur de taches IA. Pour l'objectif donne, genere un plan JSON structure avec des etapes sequentielles.

Format de reponse (JSON uniquement, rien d'autre):
{
  "objectif": "description courte de l'objectif",
  "etapes": [
    {"n": 1, "outil": "nom_outil", "desc": "ce que fait cette etape", "params": {"param1": "valeur1"}},
    {"n": 2, "outil": "nom_outil", "desc": "...", "params": {...}}
  ],
  "note": "remarque ou conseil optionnel"
}

Outils disponibles:
web_search, read_webpage, create_word, create_pdf, create_txt, read_document,
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
speak, zip_files, create_qrcode

Regles strictes:
- Maximum 6 etapes
- Une etape = un seul outil
- Les params doivent etre complets et directs (pas de placeholders comme <valeur>)
- Si l'objectif necessite 1-2 etapes seulement, mets "simple - executer directement" dans note
- Ne cree PAS de plan pour des taches simples (1 outil suffit)"""


def create_plan(goal: str) -> dict:
    """Genere un plan multi-etapes structure (JSON) pour atteindre un objectif complexe (3+ actions).
    Utilise cet outil pour les taches qui necessitent plusieurs outils en sequence."""
    key = None
    for k in ["GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3"]:
        v = os.getenv(k)
        if v and not v.startswith("AJOUTER"):
            key = v
            break
    if not key:
        return {"error": "Cle API Groq introuvable dans .env"}

    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _PLAN_SYSTEM},
                {"role": "user", "content": f"Objectif: {goal}"},
            ],
            response_format={"type": "json_object"},
            max_tokens=1024,
            temperature=0.2,
        )
        plan = json.loads(resp.choices[0].message.content)
        return {"success": True, **plan}
    except json.JSONDecodeError:
        return {"error": "Plan invalide (JSON malformate)"}
    except Exception as e:
        return {"error": str(e)}
