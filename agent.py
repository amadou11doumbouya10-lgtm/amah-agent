import os
import json
import sys
from datetime import datetime
from pathlib import Path
from groq import Groq
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS
from tools import TOOL_FUNCTIONS
from tools.memory import save_message, load_recent_messages

if getattr(sys, 'frozen', False):
    load_dotenv(Path(sys.executable).parent / '.env')
else:
    load_dotenv()

console = Console()

MAX_MESSAGES = 60  # system prompt + 60 derniers messages max


def _trim(messages: list) -> list:
    if len(messages) > MAX_MESSAGES + 1:
        return [messages[0]] + messages[-MAX_MESSAGES:]
    return messages


def execute_tool(tool_call) -> str:
    name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments) or {}
    except Exception:
        args = {}
    if not isinstance(args, dict):
        args = {}

    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return json.dumps({"error": f"Outil inconnu: {name}"}, ensure_ascii=False)

    console.print(f"  [dim #7a5f38]⟶ {name}({', '.join(f'{k}={repr(v)}' for k, v in args.items())})[/dim #7a5f38]")

    try:
        result = func(**args)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def chat(client, messages: list) -> str:
    messages = _trim(messages)

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS_DEFINITIONS,
        tool_choice="auto",
        max_tokens=2048,
        temperature=0.4,
    )

    while response.choices[0].finish_reason == "tool_calls":
        msg = response.choices[0].message
        if not msg.tool_calls:
            break

        msg_dict = {
            "role":    "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        }
        messages.append(msg_dict)

        for tool_call in msg.tool_calls:
            result = execute_tool(tool_call)
            messages.append({
                "role":         "tool",
                "tool_call_id": tool_call.id,
                "content":      result,
            })

        messages = _trim(messages)
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_DEFINITIONS,
            tool_choice="auto",
            max_tokens=2048,
            temperature=0.4,
        )

    return response.choices[0].message.content


def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        console.print("[red]Cle GROQ_API_KEY manquante dans le fichier .env[/red]")
        sys.exit(1)

    client     = Groq(api_key=api_key)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    console.print()
    console.print(Panel.fit(
        "[bold #c8a96e]THE AMAH — AGENT LOCAL[/bold #c8a96e]\n"
        f"[dim]Groq · Llama 3.3 · {len(TOOL_FUNCTIONS)} outils · Windows 11[/dim]",
        border_style="#7a5f38",
        padding=(0, 2)
    ))
    console.print()

    previous = load_recent_messages(limit=40)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + previous

    if previous:
        console.print(f"[dim #7a5f38]  {len(previous)} messages de la session precedente charges.[/dim #7a5f38]")
        console.print()

    console.print("[#c8a96e]Amah[/#c8a96e] [dim]>[/dim] Tu m'as trouvee. Qu'est-ce que tu veux faire ?")
    console.print("[dim]  ('quitter' pour terminer, 'outils' pour voir les outils)[/dim]")
    console.print()

    while True:
        try:
            user_input = console.input("[dim]Toi  >[/dim] ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["quitter", "exit", "quit", "bye"]:
                console.print("\n[#c8a96e]Amah[/#c8a96e] [dim]>[/dim] A bientot.")
                break

            if user_input.lower() == "outils":
                show_tools()
                continue

            if user_input.lower() == "reset":
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                console.print("[dim]Conversation reinitialisee.[/dim]\n")
                continue

            messages.append({"role": "user", "content": user_input})
            save_message(session_id, "user", user_input)
            console.print()

            with console.status("[dim #7a5f38]Amah reflechit...[/dim #7a5f38]",
                                spinner="dots", spinner_style="#7a5f38"):
                reply = chat(client, messages)

            messages.append({"role": "assistant", "content": reply})
            save_message(session_id, "assistant", reply)
            console.print(f"[#c8a96e]Amah[/#c8a96e] [dim]>[/dim] {reply}\n")

        except KeyboardInterrupt:
            console.print("\n[dim]Session interrompue.[/dim]")
            break
        except Exception as e:
            console.print(f"[red]Erreur: {e}[/red]\n")


def show_tools():
    console.print()
    console.print(Rule("[dim #7a5f38]OUTILS DISPONIBLES[/dim #7a5f38]", style="#2a2a27"))
    cats = {
        "Fichiers":    ["list_files", "organize_folder", "find_files", "move_file", "create_folder", "read_file", "get_folder_info"],
        "Documents":   ["create_word", "create_txt", "create_pdf", "read_document"],
        "Internet":    ["web_search", "read_webpage"],
        "Systeme":     ["get_system_info", "open_file", "run_command"],
        "Memoire":     ["save_memory", "get_memories", "delete_memory"],
        "Email":       ["read_emails", "send_email", "search_emails"],
        "Navigateur":  ["open_browser", "click_element", "fill_form", "take_screenshot", "get_page_text"],
        "Voix":        ["speak"],
        "Alertes":     ["send_notification", "set_reminder"],
        "Excel":       ["read_excel", "create_excel", "append_to_excel"],
        "Presse-pap.": ["read_clipboard", "write_clipboard"],
        "Calcul":      ["calculate", "get_datetime", "add_days", "generate_password", "convert_units"],
        "Archives":    ["zip_files", "unzip_file", "list_archive"],
        "Images":      ["screenshot_full", "resize_image", "get_image_info", "convert_image"],
        "Reseau":      ["list_processes", "get_network_info"],
    }
    for cat, tools in cats.items():
        console.print(f"  [dim #c8a96e]{cat}[/dim #c8a96e]  [dim]{' · '.join(tools)}[/dim]")
    console.print()


if __name__ == "__main__":
    main()
