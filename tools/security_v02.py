
"""Amah Agent — Security V0.2.

Lightweight tool authorization layer for the local agent.
SAFE       -> execute directly.
CONFIRM    -> ask the user in the interactive CLI.
RESTRICTED -> block by default.

This is an initial guardrail layer, not a sandbox. It is designed to reduce
accidental destructive actions while keeping ordinary agent actions usable.
Compatible with Python 3.9.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

SAFE_TOOLS = {
    "get_datetime", "calculate", "add_days", "convert_units",
    "get_weather", "get_weather_simple", "get_system_info",
    "web_search", "read_webpage", "screenshot_full", "take_screenshot",
    "find_files", "list_files", "read_file", "open_file", "open_browser",
    "get_page_text", "speak",
}

CONFIRM_TOOLS = {
    "write_file", "create_file", "edit_file", "delete_file", "move_file",
    "copy_file", "rename_file", "create_directory", "delete_directory",
    "run_command", "install_package", "open_app", "close_app",
    "fill_form", "click_element", "send_email", "send_message",
    "save_memory", "delete_memory", "set_reminder", "send_notification",
}

RESTRICTED_TOOLS = {
    "format_disk", "shutdown", "restart_system", "disable_security",
    "delete_all_files", "wipe_memory", "change_password", "steal_cookie",
}

DANGEROUS_COMMAND_PATTERNS = [
    r"\bformat\s+[a-zA-Z]:",
    r"\bdel\s+/s\s+/q\b",
    r"\brd\s+/s\s+/q\b",
    r"\brmdir\s+/s\s+/q\b",
    r"\bshutdown(?:\.exe)?\b",
    r"\bstop-computer\b",
    r"\bremove-item\b.*-recurse",
    r"\breg\s+delete\b",
    r"\bnet\s+user\b.*\/delete\b",
]
@dataclass
class Authorization:
    tool: str
    level: str
    allowed: bool
    requires_confirmation: bool
    message: str
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _command_text(args: Dict[str, Any]) -> str:
    for key in ("command", "cmd", "script"):
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def classify_tool(name: str, args: Optional[Dict[str, Any]] = None) -> str:
    args = args or {}
    tool = str(name or "").strip()
    low = tool.lower()
    if low in RESTRICTED_TOOLS:
        return "RESTRICTED"
    if low in CONFIRM_TOOLS:
        return "CONFIRM"
    if low in SAFE_TOOLS:
        return "SAFE"
    if low == "run_command":
        return "CONFIRM"
    if any(token in low for token in ("delete", "remove", "wipe", "format", "shutdown", "restart")):
        return "CONFIRM"
    return "CONFIRM"


def _confirmation_prompt(tool: str, args: Dict[str, Any]) -> str:
    if tool == "run_command":
        cmd = _command_text(args)
        preview = cmd[:240] + ("…" if len(cmd) > 240 else "")
        return f"Amah demande l'autorisation d'exécuter la commande système : {preview}\nContinuer ? [o/N] "
    return f"Amah demande l'autorisation d'utiliser l'outil sensible '{tool}'. Continuer ? [o/N] "


def authorize_tool(name: str, args: Optional[Dict[str, Any]] = None, source: str = "") -> Authorization:
    args = args or {}
    level = classify_tool(name, args)
    tool = str(name or "").strip()

    if level == "RESTRICTED":
        return Authorization(tool, level, False, False, f"Action bloquée par Security V0.2 : {tool}.", "outil explicitement restreint")

    if tool.lower() == "run_command":
        command = _command_text(args)
        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, command, flags=re.IGNORECASE):
                return Authorization(tool, "RESTRICTED", False, False, "Commande bloquée par Security V0.2 : opération système potentiellement destructive.", pattern)

    if level == "SAFE":
        return Authorization(tool, level, True, False, "Action sûre autorisée.", "outil dans la liste SAFE")

    try:
        answer = input(_confirmation_prompt(tool, args)).strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = ""

    allowed = answer in {"o", "oui", "y", "yes"}
    return Authorization(
        tool,
        level,
        allowed,
        True,
        "Action autorisée par l'utilisateur." if allowed else "Action refusée par l'utilisateur.",
        "confirmation interactive",
    )


def format_security_line(auth: Authorization) -> str:
    return (
        f"[SECURITY V0.2] outil={auth.tool} | niveau={auth.level} "
        f"| {'autorisé' if auth.allowed else 'bloqué'}"
    )

__all__ = ["Authorization", "classify_tool", "authorize_tool", "format_security_line"]
