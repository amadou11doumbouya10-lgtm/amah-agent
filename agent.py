import os
import json
import sys
import re
from datetime import datetime
from time import perf_counter
from typing import Optional, Tuple
from pathlib import Path
import unicodedata

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from dotenv import load_dotenv

from config import (
    SYSTEM_PROMPT,
    RESPONSE_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
    MODEL,
    FINAL_MODEL,
    TOOLS_DEFINITIONS,
)
from groq_client import GroqClient, repair_tool_use_failed
from tools import TOOL_FUNCTIONS, resolve_tool_name
from tools.guard import set_confirm_handler
from tools.router_v04 import normalize_for_router
from tools.router_v03 import detect_intents
from tools.tool_router import select_tools, forced_tool
from tools.fastpath_v01 import detect_fastpath
from tools.context_v01 import ConversationContext
from tools.planner_v04 import PlannerPlan, PlannerStep, build_plan
from tools.planner_v06 import build_deep_research_plan
from tools.executor_v03 import execute_verified_step_with_recovery, format_verification_line
from tools.security_v02 import authorize_tool, format_security_line
from tools.capability_bridge_v01 import build_capability_plan
from tools.voice_pipeline_v01 import (
    is_voice_listen_request,
    parse_listen_result,
    clean_for_speech,
    normalize_spoken_command,
    voice_local_clarification,
)
from tools.memory import save_message, load_resume_messages
from tools.memory_recall_v024 import format_recall
from tools.memory_context import (
    memory_context,
    memory_instruction,
    normalize_for_matching as _normalize_for_matching,
)
from tools.instant import datetime_request_kind, instant_reply as shared_instant_reply




def _strip_accents(value: str) -> str:
    """Supprime les accents pour les comparaisons lexicales locales."""
    text = str(value or "")
    return "".join(
        char for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )

# ============================================================================
# ENVIRONNEMENT
# ============================================================================

if getattr(sys, "frozen", False):
    load_dotenv(Path(sys.executable).parent / ".env")
else:
    load_dotenv()

console = Console()


class _GroqClientAdapter:
    """Expose client.chat.completions.create(...) en déléguant à GroqClient.

    Le reste du fichier garde l'API du SDK Groq, mais profite de la rotation
    des 3 clés, du repli LiteLLM et de la bascule immédiate sur 429.
    """

    def __init__(self):
        self.chat = self
        self.completions = self

    def create(self, *, model, messages, tools=None, tool_choice=None, **kwargs):
        client = GroqClient.get()
        if tools:
            return client.chat(
                messages, model, tools=tools, tool_choice=tool_choice, **kwargs
            )
        # GroqClient ignore tool_choice sans outils : on le transmet tel quel
        # (ex : "none" pour interdire tout appel d'outil).
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        return client.chat(messages, model, **kwargs)


# ============================================================================
# CONFIGURATION
# ============================================================================

MAX_MESSAGES = 60

ROUTER_MAX_TOOLS = 12

USE_MEMORY_V024 = os.getenv("AMAH_MEMORY_V024", "0") == "1"
MEMORY_STARTUP_HISTORY = 10

PERF_LOG = os.getenv("AMAH_PERF_LOG", "1") == "1"

USE_FASTPATH_V01 = os.getenv("AMAH_FASTPATH_V01", "1") == "1"
USE_PLANNER_V01 = os.getenv("AMAH_PLANNER_V01", "1") == "1"
USE_PLANNER_V04 = os.getenv("AMAH_PLANNER_V04", "1") == "1"
USE_PLANNER_V05 = os.getenv("AMAH_PLANNER_V05", "1") == "1"
USE_CAPABILITY_BRIDGE_V01 = os.getenv("AMAH_CAPABILITY_BRIDGE_V01", "1") == "1"
USE_VOICE_PIPELINE_V01 = os.getenv("AMAH_VOICE_PIPELINE_V01", "1") == "1"

# Ces outils sont déterministes et leur résultat peut être rendu directement
# sans un deuxième appel LLM.
DIRECT_RESPONSE_TOOLS = {
    "get_datetime",
    "calculate",
    "add_days",
    "convert_units",
    "screenshot_full",
    "take_screenshot",
}


# ============================================================================
# DÉTECTION MÉMOIRE
# ============================================================================

# Détection et rappel mémoire : tools/memory_context.py (partagé avec gui.py).


# ============================================================================
# PERFORMANCE / TEXTE
# ============================================================================


def _estimate_message_chars(messages: list) -> int:
    total = 0

    for message in messages:
        total += len(
            str(
                message.get(
                    "content",
                    "",
                )
                or ""
            )
        )

    return total


def _tool_name(tool_definition: dict) -> Optional[str]:
    try:
        return (
            tool_definition
            .get("function", {})
            .get("name")
        )
    except Exception:
        return None


def _trim(messages: list) -> list:
    if len(messages) > MAX_MESSAGES + 1:
        return [
            messages[0]
        ] + messages[
            -MAX_MESSAGES:
        ]

    return messages


def _get_current_user_text(
    messages: list,
) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue

        content = message.get(
            "content",
            "",
        )

        if isinstance(content, str):
            return content

    return ""


# ============================================================================
# CONTEXT COMPACT — protège le budget de contexte du LLM
# ============================================================================

CONTEXT_LLM_MAX_USER_TURNS = 3
CONTEXT_LLM_MAX_ASSISTANT_CHARS = 360
CONTEXT_LLM_MAX_USER_CHARS = 420
CONTEXT_LLM_MAX_HISTORY_CHARS = 2200


def _looks_like_tool_payload(content: str) -> bool:
    text = str(content or "").strip()
    if not text:
        return False
    if text.startswith("{") and text.endswith("}"):
        return True
    markers = (
        "\"success\":", "\"resultats\":", "Outil ",
        "[RESULTATS DES OUTILS]", "\"fichier\":", "\"temperature\":",
    )
    return any(marker in text for marker in markers)


def _compact_messages_for_llm(messages: list) -> list:
    """Conserve seulement un historique conversationnel utile et très court.

    Les gros retours d'outils sont exclus : ils sont des traces d'exécution, pas
    du contexte conversationnel stable. Le contexte actif structuré est injecté
    séparément.
    """
    if not messages:
        return messages

    system = messages[0]
    recent = []
    user_turns = 0
    history_chars = 0

    for message in reversed(messages[1:]):
        role = str(message.get("role", ""))
        content = message.get("content", "")
        if not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue

        if role == "assistant" and _looks_like_tool_payload(content):
            continue

        if role == "user":
            user_turns += 1
            if user_turns > CONTEXT_LLM_MAX_USER_TURNS:
                break
            limit = CONTEXT_LLM_MAX_USER_CHARS
        elif role == "assistant":
            limit = CONTEXT_LLM_MAX_ASSISTANT_CHARS
        else:
            continue

        compact = content[:limit].rstrip()
        if len(content) > limit:
            compact += " …"

        if history_chars + len(compact) > CONTEXT_LLM_MAX_HISTORY_CHARS:
            remaining = CONTEXT_LLM_MAX_HISTORY_CHARS - history_chars
            if remaining <= 80:
                break
            compact = compact[:remaining].rstrip() + " …"

        recent.append({"role": role, "content": compact})
        history_chars += len(compact)

        if history_chars >= CONTEXT_LLM_MAX_HISTORY_CHARS:
            break

    recent.reverse()
    return [system] + recent


# ============================================================================
# MEMORY
# ============================================================================


def _summarize_with_client(
    client,
    prompt: str,
) -> str:
    """
    Appel LLM dédié à la synthèse mémoire.
    Aucun outil n'est envoyé.
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es le module de synthèse mémoire de Amah Agent. "
                    "Retourne uniquement le JSON demandé par le prompt."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        max_tokens=900,
        temperature=0.2,
    )

    return (
        response.choices[0]
        .message
        .content
        or ""
    )


def _memory_context(
    client,
    user_text: str,
) -> Tuple[Optional[dict], bool]:
    """Retourne (résultat mémoire, réponse_directe) — voir tools/memory_context.py."""
    if not USE_MEMORY_V024:
        return None, False
    return memory_context(
        user_text,
        summarize_fn=lambda prompt: _summarize_with_client(client, prompt),
        log=(lambda message: console.print(f"[dim #7a5f38]{message}[/dim #7a5f38]")) if PERF_LOG else None,
    )


def _inject_memory_into_system(
    messages: list,
    result: dict,
) -> Optional[str]:
    """Injecte temporairement la mémoire dans le system prompt ; renvoie l'original."""
    instruction = memory_instruction(result)
    if not instruction:
        return None
    original = str(messages[0].get("content", "") or "")
    messages[0]["content"] = original + instruction
    return original


# ============================================================================
# DÉTECTION RAPIDE DATE / HEURE
# ============================================================================


_datetime_request_kind = datetime_request_kind  # tools/instant.py (partagé avec gui.py)


def _execute_tool_by_name(
    name: str,
    args: Optional[dict] = None,
    source: str = "direct",
) -> str:
    """Exécute directement un outil avec un contrôle Security V0.2."""
    args = args or {}
    name = resolve_tool_name(name)  # "tool.get_system_info" -> "get_system_info"

    authorization = authorize_tool(name=name, args=args, source=source)
    if PERF_LOG:
        console.print(format_security_line(authorization))

    if not authorization.allowed:
        return json.dumps({
            "error": authorization.message,
            "security": authorization.to_dict(),
        }, ensure_ascii=False)

    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return json.dumps(
            {"error": f"Outil inconnu: {name}"},
            ensure_ascii=False,
        )

    # Security V0.2 vient de demander l'accord pour cet outil : le garde-fou
    # central (tools/guard.py) ne doit pas reposer la question.
    _CONFIRMED_TOOL["name"] = name if authorization.requires_confirmation else None

    console.print(
        "  [dim #7a5f38]"
        f"⟶ {name}("
        + ", ".join(
            f"{k}={repr(v)}" for k, v in args.items()
        )
        + ")[/dim #7a5f38]"
    )

    try:
        result = func(**args)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    finally:
        _CONFIRMED_TOOL["name"] = None


_CONFIRMED_TOOL = {"name": None}


def _terminal_confirm(name: str, args: dict, description: str) -> bool:
    """Gestionnaire du garde-fou central pour le terminal.

    Ne redemande pas pour l'outil que Security V0.2 vient d'autoriser ; demande
    pour le reste (étapes internes d'execute_plan, open_file d'un exécutable).
    """
    if name == _CONFIRMED_TOOL["name"]:
        return True
    try:
        answer = input(
            f"Amah demande l'autorisation : {description}\nContinuer ? [o/N] "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in {"o", "oui", "y", "yes"}


set_confirm_handler(_terminal_confirm)


# Premiers mots qui désignent clairement une commande shell.
_KNOWN_COMMANDS = {
    "ipconfig", "ping", "dir", "ls", "systeminfo", "tasklist", "hostname", "whoami",
    "netstat", "nslookup", "tracert", "ver", "echo", "winget", "pip", "python", "py",
    "node", "npm", "git", "getmac", "powercfg", "where", "type", "cat", "arp", "route",
}


def _extract_system_command_request(user_text: str) -> Optional[str]:
    """Reconnaît explicitement une demande de commande système.

    Retourne la commande si elle est précisée, une chaîne vide si la demande
    est claire mais incomplète, sinon None.

    "lance Steam", "lance la musique de Stromae" ou "exécute le script x.py"
    ne sont pas des commandes : avant, tout message commençant par "lance" ou
    "exécute" partait en run_command. Seuls passent ici "exécute la commande …"
    et "lance/exécute <commande>" quand le premier mot est une vraie commande
    (ipconfig, Get-Process…).
    """
    text = str(user_text or "").strip()
    if not text:
        return None
    normalized = _strip_accents(text).lower().strip(" .!?")

    if re.fullmatch(
        r"(?:execute|lance)\s+(?:une|la)\s+commande(?:\s+(?:systeme|system|powershell))?",
        normalized,
    ):
        return ""

    explicit = re.match(
        r"^(?:execute|exécute|lance)\s+(?:la\s+|cette\s+)?commande"
        r"(?:\s+(?:systeme|système|system|powershell))?\s*[:=]?\s*(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if explicit:
        return explicit.group(1).strip()

    m = re.match(r"^(?:execute|exécute|lance)\s*:?\s+(.+)$", text, flags=re.IGNORECASE)
    if m:
        command = m.group(1).strip()
        first = command.split()[0].lower()
        if first in _KNOWN_COMMANDS or re.fullmatch(r"[a-z]+-[a-z]+", first):
            return command
    return None


# ============================================================================
# ROUTER
# ============================================================================


def _normalize_router_text(user_text: str) -> str:
    """Normalise la demande pour Router V0.4, avec correction tolérante aux fautes."""
    return normalize_for_router(user_text)


def _run_capability_bridge_workflow(user_text: str) -> Optional[str]:
    """Exécute les workflows déterministes du Capability Bridge V0.2."""
    if not USE_CAPABILITY_BRIDGE_V01:
        return None

    plan = build_capability_plan(user_text, TOOL_FUNCTIONS, max_tools=ROUTER_MAX_TOOLS)
    if not plan.workflow:
        return None

    if PERF_LOG:
        console.print(
            "[dim #7a5f38]"
            f"[CAPABILITY BRIDGE V0.2] workflow={plan.workflow} "
            f"| capacités={plan.capabilities} | confiance={plan.confidence:.2f}"
            "[/dim #7a5f38]"
        )

    if plan.workflow == "browser_voice_title":
        url = plan.workflow_args.get("url", "")
        if not url:
            return "Quelle page souhaites-tu que j'ouvre et lise à voix haute ?"
        browser_result = _execute_tool_by_name("open_browser", {"url": url}, source="capability_bridge")
        try:
            data = json.loads(browser_result)
        except Exception:
            data = {}
        if not isinstance(data, dict) or data.get("error") or not data.get("success"):
            return _pretty_tool_result("open_browser", browser_result, user_text)
        title = str(data.get("titre") or data.get("title") or "").strip()
        if not title:
            title = str(data.get("url") or url).strip()
        speak_result = _execute_tool_by_name(
            "speak",
            {"text": title},
            source="capability_bridge",
        )
        try:
            speak_data = json.loads(speak_result)
        except Exception:
            speak_data = {}
        if isinstance(speak_data, dict) and speak_data.get("error"):
            return f"J'ai ouvert la page, mais je n'ai pas pu lire le titre à voix haute : {speak_data['error']}"
        return f"J'ai ouvert la page et j'ai lu son titre à voix haute : « {title} »."

    if plan.workflow == "screen_analyze":
        result = _execute_tool_by_name(
            "analyze_screen",
            {"question": plan.workflow_args.get("question", "Décris précisément ce que tu vois sur mon écran.")},
            source="capability_bridge",
        )
        return _pretty_tool_result("analyze_screen", result, user_text)

    if plan.workflow == "file_voice_needs_path":
        return "Quel est le chemin du fichier que tu veux que je lise et te restitue à voix haute ?"

    return None


def _has_actionable_request(user_text: str) -> bool:
    """Vrai si le routeur reconnaît une action précise (météo, fichier, email…).

    "je veux connaître la météo à Paris" est une demande, pas une simple
    déclaration d'objectif : les gardes de contexte ne doivent pas l'intercepter.
    """
    _, info = select_tools(user_text, TOOLS_DEFINITIONS)
    return info["niveau"] not in ("defaut", "conversation")


def _is_local_context_update(context: ConversationContext, user_text: str) -> bool:
    """Mise à jour de contraintes ("mon budget…", "sans eSIM") à noter sans LLM."""
    if not context.is_pure_context_update(user_text) or _has_actionable_request(user_text):
        return False
    # "et pour Marseille ?" est une question de suivi, pas une contrainte : on ne
    # l'intercepte que dans une conversation sur des modèles précis.
    if re.match(r"^et\b", _normalize_for_matching(user_text)):
        return context.has_explicit_model()
    return True


def _select_tools_for_request(
    messages: list,
    planner_plan: Optional[PlannerPlan] = None,
) -> Tuple[list, list]:
    """Outils à proposer au modèle, via le routeur partagé (tools/tool_router.py).

    Liste vide uniquement pour une conversation pure ; sinon au moins le lot
    d'outils de lecture par défaut (Router V0.4 renvoyait 0 outil dans ~80 %
    des demandes réelles, et gpt-oss répondait alors à vide).
    """
    user_text = _get_current_user_text(messages)
    selected_tools, info = select_tools(
        user_text,
        TOOLS_DEFINITIONS,
        max_tools=ROUTER_MAX_TOOLS,
    )

    if PERF_LOG:
        console.print(
            "[dim #7a5f38]"
            f"[ROUTER] {len(TOOLS_DEFINITIONS)} → {len(selected_tools)} outils "
            f"| niveau={info['niveau']} | catégories={info['categories'][:4]}"
            "[/dim #7a5f38]"
        )

    return selected_tools, info["intentions"] or info["categories"] or [info["niveau"]]



# ============================================================================
# PLANNER / REASONER — EXECUTION LOCALE DU PLAN
# ============================================================================

PLANNER_RESULT_MAX_CHARS = 1800
PLANNER_RESULT_ITEM_CHARS = 320


def _compact_planner_result(result: str) -> str:
    """Réduit fortement les résultats avant synthèse pour rester sous la limite TPM."""
    raw = str(result or "")
    try:
        payload = json.loads(raw)
    except Exception:
        payload = None

    if isinstance(payload, dict):
        items = payload.get("resultats") or payload.get("results") or []
        if isinstance(items, list) and items:
            lines = []
            query = payload.get("query")
            if query:
                lines.append(f"query: {query}")
            for idx, item in enumerate(items[:5], 1):
                if not isinstance(item, dict):
                    continue
                title = str(item.get("titre") or item.get("title") or "").strip()
                url = str(item.get("url") or "").strip()
                resume = str(item.get("resume") or item.get("snippet") or item.get("description") or "").strip()
                resume = re.sub(r"\s+", " ", resume)
                parts = [f"{idx}. {title}" if title else f"{idx}."]
                if url:
                    parts.append(url)
                if resume:
                    parts.append(resume[:PLANNER_RESULT_ITEM_CHARS])
                lines.append(" — ".join(parts))
            compact = "\n".join(lines)
            if len(compact) <= PLANNER_RESULT_MAX_CHARS:
                return compact
            return compact[:PLANNER_RESULT_MAX_CHARS].rstrip() + " …"

    text = re.sub(r"\s+", " ", raw).strip()
    if len(text) <= PLANNER_RESULT_MAX_CHARS:
        return text
    return text[:PLANNER_RESULT_MAX_CHARS].rstrip() + " …"


def _execute_planner_plan(plan: PlannerPlan) -> list:
    """Execute les etapes deterministes d'un plan et valide chaque sortie.

    La validation porte sur le succes d'execution et la presence d'un resultat
    exploitable. Elle ne prouve pas a elle seule la veracite factuelle des donnees.
    """
    results = []

    for step in plan.steps:
        tool_name = step.tool_name
        if not tool_name:
            continue

        if PERF_LOG:
            console.print(
                "[dim #7a5f38]"
                f"[PLANNER V{plan.version}] étape={step.step_id} "
                f"→ {tool_name}"
                "[/dim #7a5f38]"
            )

        record_bundle = execute_verified_step_with_recovery(
            step=step,
            runner=_execute_tool_by_name,
            topic=(plan.models[0] if plan.models else ""),
            perf_log=PERF_LOG,
        )

        record = record_bundle["record"]
        results.append({
            "name": record.tool_name,
            "step_id": record.step_id,
            "action": record.action,
            "purpose": record.purpose,
            "args": record.args,
            "elapsed_ms": record.elapsed_ms,
            "result": _compact_planner_result(record.raw_result),
            "verification": record.verification.to_dict(),
        })

        if PERF_LOG:
            console.print(
                "[dim #7a5f38]"
                + format_verification_line(record)
                + "[/dim #7a5f38]"
            )

        recovery = record_bundle.get("recovery")
        if recovery:
            recovery_record = recovery["record"]
            results.append({
                "name": recovery_record.tool_name,
                "step_id": recovery_record.step_id,
                "action": recovery_record.action,
                "purpose": recovery_record.purpose,
                "args": recovery_record.args,
                "elapsed_ms": recovery_record.elapsed_ms,
                "result": _compact_planner_result(recovery_record.raw_result),
                "verification": recovery_record.verification.to_dict(),
                "recovery_for": recovery.get("for_step", step.step_id),
            })
            if PERF_LOG:
                console.print(
                    "[dim #7a5f38]"
                    + format_verification_line(recovery_record, prefix="[EXECUTOR V0.3] ")
                    + "[/dim #7a5f38]"
                )

        # Un echec d'execution ne doit pas etre masque par une synthese comme si
        # l'etape avait reussi. On conserve le resultat pour permettre au module
        # de synthese d'expliquer proprement ce qui manque.

    return results

def _finalize_planner_results(
    client,
    system_content: str,
    user_text: str,
    plan: PlannerPlan,
    tool_results: list,
) -> str:
    """Une seule synthèse LLM après exécution du plan local."""
    result_blocks = []
    for item in tool_results:
        result_blocks.append(
            f"Etape {item['step_id']} — {item['name']}\n"
            f"Objectif : {item['purpose']}\n"
            f"Paramètres : {json.dumps(item['args'], ensure_ascii=False)}\n"
            f"Résultat :\n{item['result']}"
            + "\nStatut d'exécution : "
            + str((item.get("verification") or {}).get("status", "unknown"))
            + "\nDétail de validation : "
            + str((item.get("verification") or {}).get("detail", ""))
        )

    synthesis_context = (
        f"[PLAN EXECUTE — V{plan.version}]\n"
        + plan.prompt_hint()
        + "\n\n[RESULTATS COMPACTS]\n"
        + "\n\n".join(result_blocks)
        + "\n\n"
        "Tu es le module de synthèse de Amah. Utilise uniquement les résultats ci-dessus. "
        "Les statuts CONFIRMED/SUPPORTED/UNCERTAIN/CONTRADICTED/MISSING mesurent la qualité du soutien fourni par les sources, pas une vérité absolue. "
        "Présente les faits importants, sépare clairement les modèles ou thèmes, et indique le niveau de preuve lorsque cela aide. "
        "CONFIRMED = sources pertinentes concordantes; SUPPORTED = au moins une source pertinente; UNCERTAIN = soutien faible; "
        "CONTRADICTED = sources pertinentes en conflit; MISSING = aucune preuve utile. N'invente aucun fait, prix, disponibilité, caractéristique ou compatibilité. "
        "Ne déduis jamais une caractéristique à partir d'une information commerciale indirecte (par exemple 'Cash'). Termine par une conclusion courte si les données le permettent."
    )

    synthesis_system = (
        "Tu es le module de synthèse de Amah Agent. "
        "Tu ne disposes d'aucun outil pendant cette étape. "
        "Tu dois être factuel, prudent et ne jamais inventer."
    )

    final_messages = [
        {"role": "system", "content": synthesis_system},
        {"role": "user", "content": user_text[:1200]},
        {"role": "user", "content": synthesis_context},
    ]

    started = perf_counter()
    response = client.chat.completions.create(
        model=MODEL,
        messages=final_messages,
        max_tokens=2048,
        temperature=0.3,
    )

    if PERF_LOG:
        console.print(
            "[dim #7a5f38]"
            f"[PLANNER V{plan.version}] synthèse LLM : "
            f"{(perf_counter() - started) * 1000:.1f} ms"
            "[/dim #7a5f38]"
        )

    return response.choices[0].message.content or ""

# ============================================================================
# OUTILS
# ============================================================================


def execute_tool(tool_call) -> str:
    name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments) or {}
    except Exception:
        args = {}
    if not isinstance(args, dict):
        args = {}
    if name == "get_datetime":
        args = {
            str(k).strip(): v
            for k, v in args.items()
            if str(k).strip() and v not in (None, "")
        }
    return _execute_tool_by_name(name, args, source="llm")


def _pretty_tool_result(
    tool_name: str,
    result: str,
    user_text: str = "",
) -> str:
    """
    Rend un résultat déterministe lisible sans LLM.

    get_datetime() retourne les clés `date` et `heure`.
    L'affichage dépend de la demande utilisateur.
    """

    try:
        data = json.loads(result)
    except Exception:
        return result

    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        if data.get("refuse"):
            return str(data.get("error") or "Action annulée.")
        if "error" in data:
            return f"Erreur de {tool_name} : {data['error']}"

        # Formats propres à certains outils (sinon le JSON brut était affiché)
        if tool_name == "add_days" and data.get("date"):
            jour = str(data.get("jour") or "").lower()
            return f"Dans {data.get('dans', '')}, nous serons le {jour + ' ' if jour else ''}{data['date']}."
        if tool_name == "convert_units" and data.get("formatte"):
            return str(data["formatte"])
        if tool_name == "analyze_screen" and data.get("analyse"):
            return str(data["analyse"]).strip()
        if tool_name in ("screenshot_full", "take_screenshot") and (data.get("fichier") or data.get("path")):
            return f"Capture d'écran enregistrée : {data.get('fichier') or data.get('path')}"
        if tool_name == "run_command":
            output = str(data.get("sortie") or "").strip()
            command = str(data.get("commande") or "").strip()
            if output:
                return f"Résultat de « {command} » :\n{output}"
            return f"Commande « {command} » exécutée, sans sortie."

        if tool_name == "get_datetime":
            date_value = data.get("date")
            time_value = data.get("heure") or data.get("time")
            kind = _datetime_request_kind(user_text)

            if kind == "time" and time_value:
                return f"Il est {time_value}."

            if kind == "date" and date_value:
                return f"Nous sommes le {date_value}."

            if kind == "datetime" and date_value and time_value:
                return f"Il est {time_value}, le {date_value}."

            if date_value and time_value:
                return f"Il est {time_value}, le {date_value}."
            if time_value:
                return f"Il est {time_value}."
            if date_value:
                return f"Nous sommes le {date_value}."

        # Résultats utilisateur explicites.
        for key in (
            "message",
            "text",
            "answer",
            "content",
            "result",
        ):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        if tool_name == "calculate":
            for key in (
                "value",
                "resultat",
                "result",
                "answer",
                "calculation",
            ):
                value = data.get(key)
                if value is not None:
                    return str(value)

        return json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )

    if isinstance(data, list):
        if tool_name == "web_search":
            lines = ["Voici les résultats trouvés :"]
            shown = 0
            for item in data:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or item.get("name") or "Résultat").strip()
                url = str(item.get("href") or item.get("url") or item.get("link") or "").strip()
                snippet = str(item.get("body") or item.get("snippet") or item.get("description") or "").strip()
                if url:
                    lines.append(f"- {title} — {url}")
                else:
                    lines.append(f"- {title}")
                if snippet:
                    lines.append(f"  {snippet}")
                shown += 1
                if shown >= 5:
                    break
            if shown:
                return "\n".join(lines)

        return json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )

    return str(data)


def _verify_generic_tool_result(tool_name: str, result: str) -> dict:
    """Validation legere des resultats issus d'un tool_call LLM."""
    try:
        payload = json.loads(str(result or ""))
    except Exception:
        payload = None

    if isinstance(payload, dict):
        if payload.get("success") is False or payload.get("error"):
            return {"status": "failed", "detail": str(payload.get("error") or "success=false")}
        if tool_name == "web_search":
            items = payload.get("resultats") or payload.get("results") or []
            return {
                "status": "verified" if isinstance(items, list) and items else "empty",
                "detail": f"{len(items) if isinstance(items, list) else 0} résultat(s)"
            }
        return {"status": "verified", "detail": "sortie structurée exploitable"}

    if str(result or "").strip():
        return {"status": "present", "detail": "sortie texte non structurée"}
    return {"status": "empty", "detail": "sortie vide"}


# ============================================================================
# FINALISATION LLM
# ============================================================================


def _finalize_with_llm(
    client,
    system_content: str,
    user_text: str,
    tool_results: list,
) -> str:
    """
    UN SEUL appel LLM propre après les outils.

    Aucun message assistant(tool_calls) ni role=tool n'est renvoyé au backend.
    Cela évite le conflit tool_choice observé avec gpt-oss-120b.
    """

    result_blocks = []

    for item in tool_results:
        result_blocks.append(
            "Outil "
            + item["name"]
            + " a retourné :\n"
            + item["result"]
            + "\nStatut : "
            + str((item.get("verification") or {}).get("status", "unknown"))
            + " — "
            + str((item.get("verification") or {}).get("detail", ""))
        )

    context = (
        "[RESULTATS DES OUTILS]\n"
        + "\n\n".join(result_blocks)
        + "\n\n"
        "Réponds à la demande de l'utilisateur en utilisant uniquement "
        "les résultats disponibles. Ne lance aucune nouvelle action."
    )

    # Le prompt complet (~3 600 tokens, surtout des règles de choix d'outils)
    # est inutile ici : on le remplace par RESPONSE_SYSTEM_PROMPT en gardant
    # les ajouts du tour (mémoire, contexte, plan) qui le suivent.
    if system_content.startswith(SYSTEM_PROMPT):
        system_content = (
            RESPONSE_SYSTEM_PROMPT
            + system_content[len(SYSTEM_PROMPT):]
        )

    final_messages = [
        {
            "role": "system",
            "content": system_content,
        },
        {
            "role": "user",
            "content": user_text,
        },
        {
            "role": "user",
            "content": context,
        },
    ]

    started = perf_counter()

    response = client.chat.completions.create(
        model=FINAL_MODEL,
        messages=final_messages,
        max_tokens=2048,
        temperature=0.4,
    )

    elapsed_ms = (
        perf_counter() - started
    ) * 1000

    if PERF_LOG:
        console.print(
            "[dim #7a5f38]"
            f"[LLM] finalisation : {elapsed_ms:.1f} ms"
            "[/dim #7a5f38]"
        )

    return (
        response.choices[0]
        .message
        .content
        or ""
    )


# ============================================================================
# CHAT
# ============================================================================


def chat(
    client,
    messages: list,
    context: ConversationContext,
    voice_turn: bool = False,
) -> str:
    """
    Flux principal :

        Memory
          ↓
        Router
          ↓
        premier LLM
          ↓
        outils
          ↓
        soit réponse directe,
        soit UNE finalisation LLM propre.

        Capability Bridge : unifie localement les capacités fichier / navigateur /
        voix / écran / web / système / mémoire.
    """

    messages = _trim(messages)
    user_text = _get_current_user_text(
        messages
    )

    # Garder une copie propre du system prompt.
    original_system_content = str(
        messages[0].get(
            "content",
            "",
        )
        or ""
    )

    context_hint = context.format_hint()

    try:
        # ====================================================================
        # RÉPONSES INSTANTANÉES PARTAGÉES (tools/instant.py)
        # ====================================================================
        # Heure, calcul, briefing, lecture à voix haute (lancement, arrêt) :
        # sans appel IA, comme la fenêtre et la voix. Avant, "fais-moi le point"
        # coûtait 2 appels IA, et "lis-moi à voix haute <lien>" ouvrait le
        # navigateur pour ne lire que l'adresse (banc des 3 interfaces, 18/10).
        instant = shared_instant_reply(user_text)
        if instant:
            if PERF_LOG:
                console.print("[dim #7a5f38][INSTANT] réponse sans appel IA[/dim #7a5f38]")
            return instant

        # ====================================================================
        # MEMORY
        # ====================================================================

        memory_result = None
        memory_direct = False

        if USE_MEMORY_V024:
            memory_result, memory_direct = (
                _memory_context(
                    client,
                    user_text,
                )
            )

            # Demande mémoire pure : répondre sans LLM conversationnel.
            if memory_result and memory_direct:
                formatted = format_recall(
                    memory_result
                )

                if formatted:
                    return formatted

            # Demande mémoire + action : injecter la mémoire dans le contexte.
            if memory_result and not memory_direct:
                _inject_memory_into_system(
                    messages,
                    memory_result,
                )

        # ====================================================================
        # FAST-PATH DATE / HEURE
        # ====================================================================

        datetime_kind = _datetime_request_kind(
            user_text
        )

        if datetime_kind:
            started = perf_counter()
            result = _execute_tool_by_name(
                "get_datetime",
                {},
            )

            if PERF_LOG:
                console.print(
                    "[dim #7a5f38]"
                    "[FASTPATH] get_datetime sans LLM "
                    f"| {(perf_counter() - started) * 1000:.1f} ms"
                    "[/dim #7a5f38]"
                )

            return _pretty_tool_result(
                "get_datetime",
                result,
                user_text,
            )

        # ====================================================================
        # CONTEXT GUARDS — suivis ambigus / mises à jour de contexte
        # ====================================================================

        if context.looks_like_ambiguous_model_followup(user_text):
            if PERF_LOG:
                console.print(
                    "[dim #7a5f38]"
                    "[CONTEXT] suivi de modèle ambigu → clarification locale sans LLM"
                    "[/dim #7a5f38]"
                )
            return "Quel modèle veux-tu utiliser comme référence pour la comparaison ?"

        if _is_local_context_update(context, user_text):
            if PERF_LOG:
                console.print(
                    "[dim #7a5f38]"
                    "[CONTEXT] mise à jour de contexte sans LLM"
                    "[/dim #7a5f38]"
                )
            return "D'accord, je garde cette information pour la suite."

        if context.is_context_statement(user_text) and not _has_actionable_request(user_text):
            if PERF_LOG:
                console.print(
                    "[dim #7a5f38]"
                    "[CONTEXT] objectif explicite sans action → réponse locale"
                    "[/dim #7a5f38]"
                )
            if context.topic:
                return f"D'accord. On se concentre sur {context.topic}."
            return "D'accord, j'ai bien noté ton objectif."

        # ====================================================================
        # SYSTEM COMMAND FASTPATH + SECURITY V0.2
        # ====================================================================

        system_cmd = _extract_system_command_request(user_text)
        if system_cmd is not None:
            if not system_cmd.strip():
                if PERF_LOG:
                    console.print(
                        "[dim #7a5f38][SECURITY V0.2] commande système manquante → clarification locale sans LLM[/dim #7a5f38]"
                    )
                return "Quelle commande système souhaites-tu exécuter exactement ?"

            started = perf_counter()
            result = _execute_tool_by_name(
                "run_command",
                {"command": system_cmd},
                source="system_command_fastpath",
            )
            elapsed_ms = (perf_counter() - started) * 1000
            if PERF_LOG:
                console.print(
                    "[dim #7a5f38][FASTPATH V1.4] run_command contrôlé par Security V0.2"
                    f" | {elapsed_ms:.1f} ms[/dim #7a5f38]"
                )
            return _pretty_tool_result("run_command", result, user_text)

        # ====================================================================
        # CAPABILITY BRIDGE V0.2 — WORKFLOWS DETERMINISTES
        # ====================================================================

        capability_reply = _run_capability_bridge_workflow(user_text)
        if capability_reply is not None:
            return capability_reply

        # ====================================================================
        # PLANNER V0.6 — RECHERCHE APPROFONDIE
        # ====================================================================

        if USE_PLANNER_V05:
            deep_plan = build_deep_research_plan(
                user_text,
                context,
            )

            if deep_plan and deep_plan.kind == "clarification":
                if PERF_LOG:
                    console.print(
                        "[dim #7a5f38]"
                        "[PLANNER V0.6] clarification locale sans LLM"
                        "[/dim #7a5f38]"
                    )
                return deep_plan.clarification

            if deep_plan and deep_plan.executable:
                if PERF_LOG:
                    console.print(
                        "[dim #7a5f38]"
                        f"[PLANNER V0.6] type={deep_plan.kind} "
                        f"| etapes={len(deep_plan.steps)} "
                        f"| sujet={deep_plan.models[0] if deep_plan.models else ''}"
                        "[/dim #7a5f38]"
                    )

                planner_system = (
                    original_system_content
                    + ("\n\n" + context_hint if context_hint else "")
                ).strip()

                planner_results = _execute_planner_plan(deep_plan)
                if not planner_results:
                    return "Je n'ai pas pu exécuter les recherches prévues."

                return _finalize_planner_results(
                    client,
                    planner_system,
                    user_text,
                    deep_plan,
                    planner_results,
                )

        # ====================================================================
        # FASTPATH V1 — ACTIONS SIMPLES SANS LLM
        # ====================================================================

        if USE_FASTPATH_V01:
            fastpath = detect_fastpath(
                user_text,
                TOOL_FUNCTIONS,
                context,
            )

            if fastpath:
                if fastpath.get("kind") == "reply":
                    if PERF_LOG:
                        console.print(
                            "[dim #7a5f38]"
                            "[FASTPATH V1] réponse locale sans LLM"
                            f" | {fastpath.get('label', 'commande')}"
                            "[/dim #7a5f38]"
                        )
                    return str(
                        fastpath.get(
                            "response",
                            "",
                        )
                    )

                if fastpath.get("kind") == "tool":
                    tool_name = fastpath.get(
                        "tool_name"
                    )
                    tool_args = fastpath.get(
                        "args",
                        {},
                    )

                    if tool_name:
                        started = perf_counter()
                        result = _execute_tool_by_name(
                            tool_name,
                            tool_args,
                        )

                        elapsed_ms = (
                            perf_counter() - started
                        ) * 1000

                        if PERF_LOG:
                            console.print(
                                "[dim #7a5f38]"
                                "[FASTPATH V1] "
                                f"{tool_name} sans LLM"
                                f" | {elapsed_ms:.1f} ms"
                                "[/dim #7a5f38]"
                            )

                        # Une liste de liens ne répond pas à la question :
                        # courte synthèse par FINAL_MODEL (quota séparé).
                        if tool_name == "web_search":
                            return _finalize_with_llm(
                                client,
                                original_system_content,
                                user_text,
                                [{
                                    "name": tool_name,
                                    "result": result[:2000],
                                    "verification": _verify_generic_tool_result(tool_name, result),
                                }],
                            )

                        return _pretty_tool_result(
                            tool_name,
                            result,
                            user_text,
                        )

        # ====================================================================
        # PLANNER / REASONER
        # ====================================================================

        planner_plan = None
        if USE_PLANNER_V04:
            planner_plan = build_plan(
                user_text,
                context,
            )

            if planner_plan and planner_plan.kind == "clarification":
                if PERF_LOG:
                    console.print(
                        "[dim #7a5f38]"
                        "[PLANNER V0.4] clarification locale sans LLM"
                        "[/dim #7a5f38]"
                    )
                return planner_plan.clarification

            if planner_plan and PERF_LOG:
                console.print(
                    "[dim #7a5f38]"
                    f"[PLANNER V0.4] type={planner_plan.kind} "
                    f"| etapes={len(planner_plan.steps)} "
                    f"| outils={planner_plan.tools}"
                    "[/dim #7a5f38]"
                )

            # Les plans exécutables sont traités localement : pas de premier
            # appel LLM pour choisir les outils, puis une seule synthèse finale.
            if planner_plan and planner_plan.executable:
                planner_system = (
                    original_system_content
                    + ("\n\n" + context_hint if context_hint else "")
                ).strip()

                planner_results = _execute_planner_plan(planner_plan)

                if not planner_results:
                    return "Je n'ai pas pu exécuter les étapes prévues par le plan."

                return _finalize_planner_results(
                    client,
                    planner_system,
                    user_text,
                    planner_plan,
                    planner_results,
                )

        # ====================================================================
        # ROUTER
        # ====================================================================

        available_tools, intents = (
            _select_tools_for_request(
                messages,
                planner_plan,
            )
        )

        if PERF_LOG:
            console.print(
                "[dim #7a5f38]"
                f"[PERF] outils disponibles : "
                f"{len(available_tools)}"
                f" | intentions={intents}"
                f" | messages={len(messages)}"
                f" | chars={_estimate_message_chars(messages)}"
                "[/dim #7a5f38]"
            )

        # ====================================================================
        # PAS D'OUTIL
        # ====================================================================

        if not available_tools and voice_turn:
            return "Je n'ai pas reconnu cette commande vocale. Peux-tu la reformuler plus simplement ?"

        if not available_tools:
            # Conversation pure (le routeur ne renvoie 0 outil que dans ce cas) :
            # prompt court au lieu de SYSTEM_PROMPT (~3 700 tokens de règles
            # d'outils), sur le modèle léger comme gui.py. Le contexte n'est
            # ajouté qu'une fois (il l'était deux fois auparavant).
            llm_messages = _compact_messages_for_llm(messages)
            llm_messages[0]["content"] = (
                CHAT_SYSTEM_PROMPT
                + ("\n\n" + context_hint if context_hint else "")
            )

            request_kwargs = {
                "model": FINAL_MODEL,
                "messages": llm_messages,
                "max_tokens": 2048,
                "temperature": 0.4,
                "tool_choice": "none",
            }

            started = perf_counter()

            try:
                response = client.chat.completions.create(
                    **request_kwargs
                )
            except Exception as exc:
                # Le router n'a proposé aucun outil mais le modèle en appelle un
                # quand même (ex : web_search sur une question factuelle) →
                # Groq renvoie 400 tool_use_failed. On exécute l'appel (contrôlé
                # par Security V0.2) puis on finalise au lieu de planter.
                repaired = repair_tool_use_failed(exc)
                if not repaired:
                    raise
                tool_name, tool_args = repaired
                result = _execute_tool_by_name(
                    tool_name, tool_args, source="repair"
                )
                return _finalize_with_llm(
                    client,
                    llm_messages[0]["content"],
                    user_text,
                    [{
                        "name": tool_name,
                        "result": result[:2000],
                        "verification": _verify_generic_tool_result(tool_name, result),
                    }],
                )

            if PERF_LOG:
                console.print(
                    "[dim #7a5f38]"
                    f"[LLM] appel direct : "
                    f"{(perf_counter() - started) * 1000:.1f} ms"
                    "[/dim #7a5f38]"
                )

            return (
                response.choices[0]
                .message
                .content
                or ""
            )

        # ====================================================================
        # PREMIER APPEL LLM + OUTILS
        # ====================================================================

        tool_names = [
            _tool_name(tool)
            for tool in available_tools
        ]
        tool_names = [
            name
            for name in tool_names
            if name
        ]

        tool_system_content = (
            str(
                messages[0].get(
                    "content",
                    "",
                )
                or ""
            )
            + ("\n\n" + context_hint if context_hint else "")
            + ("\n\n" + planner_plan.prompt_hint() if planner_plan else "")
            + "\n\n"
            "[OUTILS DISPONIBLES POUR CE TOUR]\n"
            + ", ".join(tool_names)
            + "\nUtilise uniquement les outils réellement fournis. "
            "N'invente aucun autre nom d'outil.\n"
        )

        messages[0]["content"] = (
            tool_system_content
        )

        llm_messages = _compact_messages_for_llm(messages)
        # Le system prompt doit porter le contexte et les outils sélectionnés.
        llm_messages[0]["content"] = str(messages[0].get("content", "") or "")

        request_kwargs = {
            "model": MODEL,
            "messages": llm_messages,
            "tools": available_tools,
            "max_tokens": 2048,
            "temperature": 0.4,
        }

        # Une seule fonction : on impose précisément cette fonction.
        # Question d'actualité sans outil précis : recherche web imposée.
        forced = forced_tool(user_text, available_tools)
        if forced or (len(available_tools) == 1 and tool_names):
            request_kwargs[
                "tool_choice"
            ] = {
                "type": "function",
                "function": {
                    "name": forced or tool_names[0],
                },
            }
        else:
            request_kwargs[
                "tool_choice"
            ] = "auto"

        llm_started = perf_counter()

        response = client.chat.completions.create(
            **request_kwargs
        )

        if PERF_LOG:
            console.print(
                "[dim #7a5f38]"
                f"[LLM] premier appel : "
                f"{(perf_counter() - llm_started) * 1000:.1f} ms"
                "[/dim #7a5f38]"
            )

        # ====================================================================
        # LE MODÈLE N'A PAS APPELÉ D'OUTIL
        # ====================================================================

        if response.choices[0].finish_reason != "tool_calls":
            return (
                response.choices[0]
                .message
                .content
                or ""
            )

        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content or ""

        # ====================================================================
        # EXÉCUTER LE LOT D'OUTILS
        # ====================================================================

        tool_results = []

        for tool_call in msg.tool_calls:
            tool_result = execute_tool(
                tool_call
            )

            verification = _verify_generic_tool_result(
                tool_call.function.name,
                tool_result,
            )

            tool_results.append(
                {
                    "name": tool_call.function.name,
                    "result": tool_result,
                    "verification": verification,
                }
            )

        # ====================================================================
        # RÉPONSE DIRECTE POUR LES OUTILS DÉTERMINISTES
        # ====================================================================

        if (
            len(tool_results) == 1
            and tool_results[0]["name"]
            in DIRECT_RESPONSE_TOOLS
            and not (planner_plan and planner_plan.requires_synthesis)
        ):
            return _pretty_tool_result(
                tool_results[0]["name"],
                tool_results[0]["result"],
                user_text,
            )

        # ====================================================================
        # FINALISATION LLM PROPRE
        # ====================================================================

        # Utiliser le system prompt enrichi par Memory, mais jamais le protocole
        # assistant(tool_calls) / role=tool.
        final_system = str(
            messages[0].get(
                "content",
                "",
            )
            or ""
        )

        # On retire de ce prompt la liste des outils : il n'y a plus d'outils
        # disponibles pendant la finalisation.
        final_system = re.sub(
            r"\n\n\[OUTILS DISPONIBLES POUR CE TOUR\].*",
            "",
            final_system,
            flags=re.DOTALL,
        ).strip()

        return _finalize_with_llm(
            client,
            final_system,
            user_text,
            tool_results,
        )

    finally:
        # Ne jamais laisser la mémoire ou les instructions outils s'accumuler
        # dans le system prompt de la session locale.
        if messages:
            messages[0]["content"] = (
                original_system_content
            )


# ============================================================================
# MAIN
# ============================================================================


def main():
    api_key = os.getenv(
        "GROQ_API_KEY"
    )

    if not api_key:
        console.print(
            "[red]"
            "Cle GROQ_API_KEY manquante dans le fichier .env"
            "[/red]"
        )
        sys.exit(1)

    client = _GroqClientAdapter()

    session_id = (
        datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    console.print()

    console.print(
        Panel.fit(
            "[bold #c8a96e]"
            "THE AMAH — AGENT LOCAL"
            "[/bold #c8a96e]\n"
            f"[dim]Groq · {MODEL} · "
            f"{len(TOOL_FUNCTIONS)} outils · Windows 11 · "
            f"Router V0.4 · Memory V0.2.4 · Context V0.7 · FastPath V1.4 · Args V0.2 · Planner V0.6 · Executor V0.3 · Verification V0.3 · Capability Bridge V0.2 · Voice Pipeline V0.3[/dim]",
            border_style="#7a5f38",
            padding=(0, 2),
        )
    )

    console.print()

    history_limit = (
        MEMORY_STARTUP_HISTORY
        if USE_MEMORY_V024
        else 40
    )

    # Dernière session seulement, si elle date de moins de 12 h, sans question
    # restée sans réponse (voir tools/memory.py, load_resume_messages).
    previous = load_resume_messages(
        limit=history_limit
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ] + previous

    conversation_context = ConversationContext.from_messages(
        previous
    )

    if PERF_LOG:
        console.print(
            "[dim #7a5f38]"
            f"[MEMORY] V0.2.4="
            f"{'ON' if USE_MEMORY_V024 else 'OFF'}"
            f" | historique initial="
            f"{len(previous)}"
            f" | caracteres="
            f"{_estimate_message_chars(messages)}"
            "[/dim #7a5f38]"
        )

    if previous:
        console.print(
            "[dim #7a5f38]"
            f"  {len(previous)} messages de la "
            "session precedente charges."
            "[/dim #7a5f38]"
        )
        console.print()

    console.print(
        "[#c8a96e]Amah[/#c8a96e] [dim]>[/dim] "
        "Tu m'as trouvee. Qu'est-ce que tu veux faire ?"
    )

    console.print(
        "[dim]"
        "  ('quitter' pour terminer, 'outils' pour voir les outils)"
        "[/dim]"
    )

    console.print()

    while True:
        try:
            user_input = console.input(
                "[dim]Toi  >[/dim] "
            ).strip()

            if not user_input:
                continue

            if user_input.lower() in [
                "quitter",
                "exit",
                "quit",
                "bye",
            ]:
                console.print(
                    "\n[#c8a96e]Amah[/#c8a96e] [dim]>[/dim] A bientot."
                )
                break

            if user_input.lower() == "outils":
                show_tools()
                continue

            if user_input.lower() == "reset":
                messages = [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    }
                ]

                conversation_context = ConversationContext()

                session_id = (
                    datetime.now()
                    .strftime(
                        "%Y%m%d_%H%M%S"
                    )
                )

                console.print(
                    "[dim]"
                    "Conversation reinitialisee."
                    "[/dim]\n"
                )
                continue

            # ====================================================================
            # VOICE PIPELINE V0.3
            # Déclenche l'écoute locale avant le pipeline normal, puis réinjecte
            # le texte reconnu comme une commande utilisateur ordinaire.
            # ====================================================================
            voice_turn = False
            if USE_VOICE_PIPELINE_V01 and is_voice_listen_request(user_input):
                raw_listen = _execute_tool_by_name(
                    "listen",
                    {"timeout": 7, "language": "fr-FR"},
                    source="voice_pipeline",
                )
                ok, recognized_text, error_text = parse_listen_result(raw_listen)

                if not ok:
                    console.print(
                        "[red]"
                        f"[VOICE PIPELINE V0.3] {error_text}"
                        "[/red]\n"
                    )
                    continue

                voice_turn = True
                user_input = normalize_spoken_command(recognized_text)
                local_clarification = voice_local_clarification(user_input)
                if local_clarification:
                    if PERF_LOG:
                        console.print(
                            "[dim #7a5f38]"
                            f"[VOICE PIPELINE V0.3] clarification locale : {local_clarification}"
                            "[/dim #7a5f38]"
                        )
                    _execute_tool_by_name(
                        "speak",
                        {"text": local_clarification},
                        source="voice_pipeline",
                    )
                    console.print(
                        f"[#c8a96e]Amah[/#c8a96e] [dim]>[/dim] {local_clarification}\n"
                    )
                    continue
                if PERF_LOG:
                    console.print(
                        "[dim #7a5f38]"
                        f"[VOICE PIPELINE V0.3] texte reconnu : {recognized_text}"
                        + (f" → normalisé : {user_input}" if user_input != recognized_text else "")
                        + "[/dim #7a5f38]"
                    )

            messages.append(
                {
                    "role": "user",
                    "content": user_input,
                }
            )

            conversation_context.ingest(user_input)

            if PERF_LOG:
                summary = conversation_context.summary_line()
                if summary:
                    console.print(
                        "[dim #7a5f38]"
                        f"[CONTEXT] {summary}"
                        "[/dim #7a5f38]"
                    )

            save_message(
                session_id,
                "user",
                user_input,
            )

            console.print()

            with console.status(
                "[dim #7a5f38]"
                "Amah reflechit..."
                "[/dim #7a5f38]",
                spinner="dots",
                spinner_style="#7a5f38",
            ):
                try:
                    reply = chat(
                        client,
                        messages,
                        conversation_context,
                        voice_turn=voice_turn,
                    )
                except Exception as exc:
                    # Une erreur API/outil ne doit pas fermer la session.
                    reply = f"Désolé, une erreur est survenue : {exc}"

            messages.append(
                {
                    "role": "assistant",
                    "content": reply,
                }
            )

            if voice_turn and USE_VOICE_PIPELINE_V01:
                spoken = clean_for_speech(reply)
                if spoken:
                    if PERF_LOG:
                        console.print(
                            "[dim #7a5f38]"
                            "[VOICE PIPELINE V0.3] réponse vocale"
                            "[/dim #7a5f38]"
                        )
                    _execute_tool_by_name(
                        "speak",
                        {"text": spoken},
                        source="voice_pipeline",
                    )

            save_message(
                session_id,
                "assistant",
                reply,
            )

            console.print(
                "[#c8a96e]Amah[/#c8a96e] [dim]>[/dim] "
                f"{reply}\n"
            )

        except KeyboardInterrupt:
            console.print(
                "\n[dim]Session interrompue.[/dim]"
            )
            break

        except Exception as exc:
            console.print(
                "[red]"
                f"Erreur: {exc}"
                "[/red]\n"
            )


# ============================================================================
# AFFICHAGE DES OUTILS
# ============================================================================


def show_tools():
    console.print()

    console.print(
        Rule(
            "[dim #7a5f38]"
            "OUTILS DISPONIBLES"
            "[/dim #7a5f38]",
            style="#2a2a27",
        )
    )

    cats = {
        "Fichiers": [
            "list_files",
            "organize_folder",
            "find_files",
            "move_file",
            "create_folder",
            "read_file",
            "get_folder_info",
        ],
        "Documents": [
            "create_word",
            "create_txt",
            "create_pdf",
            "read_document",
        ],
        "Internet": [
            "web_search",
            "read_webpage",
        ],
        "Systeme": [
            "get_system_info",
            "open_file",
            "run_command",
        ],
        "Memoire": [
            "save_memory",
            "get_memories",
            "delete_memory",
        ],
        "Email": [
            "read_emails",
            "send_email",
            "search_emails",
        ],
        "Navigateur": [
            "open_browser",
            "click_element",
            "fill_form",
            "take_screenshot",
            "get_page_text",
        ],
        "Voix": [
            "speak",
        ],
        "Pont capacites": [
            "capability_bridge_v01",
        ],
        "Alertes": [
            "send_notification",
            "set_reminder",
        ],
        "Excel": [
            "read_excel",
            "create_excel",
            "append_to_excel",
        ],
        "Presse-pap.": [
            "read_clipboard",
            "write_clipboard",
        ],
        "Calcul": [
            "calculate",
            "get_datetime",
            "add_days",
            "generate_password",
            "convert_units",
        ],
        "Archives": [
            "zip_files",
            "unzip_file",
            "list_archive",
        ],
        "Images": [
            "screenshot_full",
            "resize_image",
            "get_image_info",
            "convert_image",
        ],
        "Reseau": [
            "list_processes",
            "get_network_info",
        ],
    }

    for category, tools in cats.items():
        console.print(
            f"  [dim #c8a96e]"
            f"{category}"
            f"[/dim #c8a96e]  "
            f"[dim]"
            f"{' · '.join(tools)}"
            f"[/dim]"
        )

    console.print()


if __name__ == "__main__":
    main()
