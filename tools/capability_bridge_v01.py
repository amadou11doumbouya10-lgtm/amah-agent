"""Amah Agent — Capability Bridge V0.2

Unifie les capacités et ajoute quelques workflows déterministes pour éviter
un détour LLM quand la séquence d'actions est parfaitement connue.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence


@dataclass
class CapabilityPlan:
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    confidence: float = 0.0
    workflow: str = ""
    workflow_args: Dict[str, str] = field(default_factory=dict)


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


CAPABILITY_PATTERNS: Dict[str, Sequence[str]] = {
    "browser": (
        "ouvre le site", "ouvre ce site", "ouvre cette page",
        "va sur le site", "va sur cette page", "navigue sur",
        "clique sur", "remplis le formulaire", "remplir le formulaire",
        "utilise le navigateur", "dans le navigateur",
    ),
    "files": (
        "lis ce fichier", "ouvre ce fichier", "lire ce fichier",
        "ouvre le fichier", "lis le document", "ouvre le document",
        "trouve le fichier", "cherche le fichier", "fichier pdf",
        "dans mon dossier", "dans mes fichiers",
    ),
    "voice": (
        "à voix haute", "a voix haute", "lis-moi", "lis moi",
        "fais-moi écouter", "fais moi ecouter", "prononce",
        "dis-le à voix haute", "dis le a voix haute",
    ),
    "screen": (
        "regarde mon écran", "regarde mon ecran", "analyse mon écran",
        "analyse mon ecran", "ce qu'il y a sur mon écran",
        "ce qu il y a sur mon ecran",
        # "capture d'écran" retiré : c'est une demande d'enregistrer l'image
        # (FastPath screenshot), pas de la faire analyser par l'IA.
        "explique ce que tu vois sur mon écran",
        "explique ce que tu vois sur mon ecran",
    ),
    "web": (
        "cherche sur google", "cherche sur internet", "recherche sur internet",
        "cherche sur le web", "recherche sur le web", "recherche web",
        "cherche-moi", "cherche moi",
    ),
    "system": (
        "exécute", "execute", "lance une commande",
        "commande système", "commande systeme",
    ),
    "memory": (
        "tu te souviens", "rappelle-moi", "rappelle moi",
        "qu'est-ce qu'on avait dit", "qu est ce qu on avait dit",
    ),
}

TOOL_HINTS: Dict[str, Sequence[str]] = {
    "browser": ("open_browser", "click_element", "fill_form", "get_page_text", "take_screenshot"),
    "files": ("find_files", "read_file", "open_file", "list_files", "get_folder_info"),
    "voice": ("speak",),
    "screen": ("screenshot_full", "take_screenshot", "analyze_screen", "analyze_image", "vision", "webcam"),
    "web": ("web_search", "read_webpage", "open_browser"),
    "system": ("run_command", "get_system_info"),
    "memory": ("get_memories", "save_memory"),
}

VOICE_RE = re.compile(r"(?:à|a) voix haute|lis(?:-moi| moi)|fais(?:-moi| moi) (?:écouter|ecouter)|prononce|dis(?:-le| le) (?:à|a) voix haute", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)


def _find_available_tools(tool_functions: Dict[str, object], hints: Iterable[str]) -> List[str]:
    names = list(tool_functions.keys())
    out: List[str] = []
    for hint in hints:
        if hint in tool_functions and hint not in out:
            out.append(hint)
            continue
        hint_l = hint.lower()
        if hint_l in {"analyze_screen", "analyze_image", "vision", "webcam"}:
            for name in names:
                nl = name.lower()
                if hint_l in nl or ("screen" in nl and "analys" in nl) or ("vision" in nl):
                    if name not in out:
                        out.append(name)
    return out


def build_capability_plan(user_text: str, tool_functions: Dict[str, object], max_tools: int = 6) -> CapabilityPlan:
    text = _normalized(user_text)
    if not text:
        return CapabilityPlan()

    capabilities: List[str] = []
    for capability, patterns in CAPABILITY_PATTERNS.items():
        if any(pattern in text for pattern in patterns):
            capabilities.append(capability)

    url_match = URL_RE.search(text)
    if url_match and "browser" not in capabilities:
        capabilities.append("browser")

    # Workflows déterministes : on évite ici tout appel LLM.
    if "browser" in capabilities and "voice" in capabilities and url_match:
        return CapabilityPlan(
            capabilities=capabilities,
            tools=[name for name in ("open_browser", "speak") if name in tool_functions],
            confidence=0.98,
            workflow="browser_voice_title",
            workflow_args={"url": url_match.group(0).rstrip(".,;:!?)]}" )},
        )

    if "screen" in capabilities and "analyze_screen" in tool_functions:
        return CapabilityPlan(
            capabilities=capabilities,
            tools=[name for name in ("analyze_screen",) if name in tool_functions],
            confidence=0.96,
            workflow="screen_analyze",
            workflow_args={"question": "Décris précisément ce que tu vois sur mon écran."},
        )

    if "files" in capabilities and "voice" in capabilities:
        return CapabilityPlan(
            capabilities=capabilities,
            tools=[name for name in ("find_files", "read_file", "speak") if name in tool_functions],
            confidence=0.78,
            workflow="file_voice_needs_path",
        )

    tools: List[str] = []
    for capability in capabilities:
        for name in _find_available_tools(tool_functions, TOOL_HINTS.get(capability, ())):
            if name not in tools:
                tools.append(name)
            if len(tools) >= max_tools:
                break
        if len(tools) >= max_tools:
            break

    confidence = min(0.99, 0.55 + 0.12 * len(capabilities)) if capabilities else 0.0
    return CapabilityPlan(capabilities=capabilities, tools=tools[:max_tools], confidence=confidence)


def merge_tools(primary: List[dict], capability_plan: CapabilityPlan, all_definitions: List[dict], max_tools: int = 6) -> List[dict]:
    by_name = {}
    for tool in all_definitions:
        function = tool.get("function") if isinstance(tool, dict) else None
        if isinstance(function, dict) and function.get("name"):
            by_name[str(function["name"])] = tool
        elif isinstance(tool, dict) and tool.get("name"):
            by_name[str(tool["name"])] = tool

    result = list(primary)
    existing = set()
    for tool in result:
        function = tool.get("function") if isinstance(tool, dict) else None
        name = function.get("name") if isinstance(function, dict) else tool.get("name") if isinstance(tool, dict) else None
        if name:
            existing.add(str(name))

    for name in capability_plan.tools:
        if name in existing or name not in by_name:
            continue
        result.append(by_name[name])
        existing.add(name)
        if len(result) >= max_tools:
            break

    return result[:max_tools]


__all__ = ["CapabilityPlan", "build_capability_plan", "merge_tools"]
