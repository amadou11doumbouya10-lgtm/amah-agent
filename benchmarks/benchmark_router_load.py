"""
Amah Agent - Benchmark Router Load

Compare la charge des définitions d'outils :

    A) Tous les outils actuels
    B) Outils sélectionnés par Router V0.3

Aucun appel API n'est effectué.
Aucun outil réel n'est exécuté.
"""

from __future__ import annotations

import json

from config import SYSTEM_PROMPT, TOOLS_DEFINITIONS
from tools.router_v03 import route_tools


# ============================================================================
# TESTS
# ============================================================================

TESTS = [
    "Quelle est la météo actuelle à Conakry ?",
    "Montre-moi le contenu de contrat.pdf",
    "Peux-tu retrouver mon fichier CV ?",
    "Supprime ce fichier",
    "Modifie mon fichier config.py",
    "Montre-moi les processus qui tournent actuellement",
    "Donne-moi les caractéristiques de mon ordinateur",
    "Envoie ce message par email",
    "Garde ça en mémoire",
    "Rappelle-moi ce que tu sais de mon projet",
    "Ouvre Steam",
    "Cherche GTA sur Steam",
    "Installe GTA sur Steam",
    "Prends une capture de l'écran",
    "Regarde ce qu'il y a sur mon écran",
    "Va sur YouTube",
    "Cherche cette vidéo sur YouTube",
    "Écris une fonction Python",
    "Exécute mon script Python",
    "Salut Amah",
    "Merci Amah",
    "Qu'est-ce que tu peux faire ?",
    "Calcule 250000 * 37",
    "Quelle heure est-il ?",
]


# ============================================================================
# UTILITAIRES
# ============================================================================

def serialize_tools(tools: list[dict]) -> str:
    """
    Sérialise les définitions comme dans une requête JSON.
    """

    return json.dumps(
        tools,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def approximate_tokens(text: str) -> int:
    """
    Approximation grossière du nombre de tokens.

    Ce n'est PAS le tokenizer réel de Groq.
    On l'utilise uniquement pour comparer AVANT / APRÈS.
    """

    return max(1, len(text) // 4)


def format_number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def analyze_tools(tools: list[dict]) -> dict[str, int]:

    serialized = serialize_tools(tools)

    return {
        "tools": len(tools),
        "chars": len(serialized),
        "bytes": len(serialized.encode("utf-8")),
        "approx_tokens": approximate_tokens(serialized),
    }


# ============================================================================
# CHARGE DE BASE
# ============================================================================

all_stats = analyze_tools(TOOLS_DEFINITIONS)

system_chars = len(SYSTEM_PROMPT)
system_tokens = approximate_tokens(SYSTEM_PROMPT)


print()
print("=" * 80)
print(" AMAH AGENT — BENCHMARK CHARGE ROUTER V0.3")
print("=" * 80)
print()

print("DEFINITIONS ACTUELLES")
print("-" * 80)
print(f"Outils             : {format_number(all_stats['tools'])}")
print(f"Caractères         : {format_number(all_stats['chars'])}")
print(f"Octets             : {format_number(all_stats['bytes'])}")
print(f"Tokens approx.     : {format_number(all_stats['approx_tokens'])}")
print()

print("SYSTEM PROMPT")
print("-" * 80)
print(f"Caractères         : {format_number(system_chars)}")
print(f"Tokens approx.     : {format_number(system_tokens)}")
print()


# ============================================================================
# TESTS ROUTER
# ============================================================================

total_before_chars = 0
total_after_chars = 0

total_before_tokens = 0
total_after_tokens = 0

total_selected_tools = 0


for i, text in enumerate(TESTS, start=1):

    selected, intents = route_tools(
        text,
        TOOLS_DEFINITIONS,
        max_tools=12,
    )

    before = all_stats
    after = analyze_tools(selected)

    total_before_chars += before["chars"]
    total_after_chars += after["chars"]

    total_before_tokens += before["approx_tokens"]
    total_after_tokens += after["approx_tokens"]

    total_selected_tools += after["tools"]

    if before["chars"] > 0:
        reduction_chars = (
            1 - (after["chars"] / before["chars"])
        ) * 100
    else:
        reduction_chars = 0

    if before["approx_tokens"] > 0:
        reduction_tokens = (
            1 - (after["approx_tokens"] / before["approx_tokens"])
        ) * 100
    else:
        reduction_tokens = 0

    print("=" * 80)
    print(f"TEST {i}")
    print("=" * 80)

    print(f"Demande            : {text}")
    print(f"Intentions         : {intents}")
    print()

    print("AVANT")
    print(f"  Outils           : {before['tools']}")
    print(f"  Caractères       : {format_number(before['chars'])}")
    print(f"  Tokens approx.   : {format_number(before['approx_tokens'])}")

    print()

    print("APRÈS ROUTER V0.3")
    print(f"  Outils           : {after['tools']}")
    print(f"  Caractères       : {format_number(after['chars'])}")
    print(f"  Tokens approx.   : {format_number(after['approx_tokens'])}")

    print()

    print("RÉDUCTION")
    print(f"  Caractères       : {reduction_chars:.2f} %")
    print(f"  Tokens approx.   : {reduction_tokens:.2f} %")

    print()

    print("OUTILS SÉLECTIONNÉS")

    for tool in selected:
        try:
            print(f"  - {tool['function']['name']}")
        except (KeyError, TypeError):
            print("  - [outil invalide]")

    print()


# ============================================================================
# MOYENNES
# ============================================================================

number_tests = len(TESTS)

avg_before_chars = total_before_chars // number_tests
avg_after_chars = total_after_chars // number_tests

avg_before_tokens = total_before_tokens // number_tests
avg_after_tokens = total_after_tokens // number_tests

avg_tools = total_selected_tools / number_tests


if total_before_chars:
    global_chars_reduction = (
        1 - (total_after_chars / total_before_chars)
    ) * 100
else:
    global_chars_reduction = 0


if total_before_tokens:
    global_tokens_reduction = (
        1 - (total_after_tokens / total_before_tokens)
    ) * 100
else:
    global_tokens_reduction = 0


if all_stats["tools"]:
    avg_tool_reduction = (
        1 - (avg_tools / all_stats["tools"])
    ) * 100
else:
    avg_tool_reduction = 0


# ============================================================================
# RÉSULTAT FINAL
# ============================================================================

print("=" * 80)
print(" RÉSULTAT GLOBAL")
print("=" * 80)
print()

print(f"Nombre de tests                    : {number_tests}")
print()

print("OUTILS")
print("-" * 80)
print(f"Avant                               : {all_stats['tools']}")
print(f"Moyenne après Router V0.3           : {avg_tools:.2f}")
print(f"Réduction moyenne                   : {avg_tool_reduction:.2f} %")
print()

print("CARACTÈRES")
print("-" * 80)
print(f"Avant / requête                     : {format_number(all_stats['chars'])}")
print(f"Après / requête                     : {format_number(avg_after_chars)}")
print(f"Réduction globale                   : {global_chars_reduction:.2f} %")
print()

print("TOKENS APPROXIMATIFS")
print("-" * 80)
print(f"Avant / requête                     : {format_number(all_stats['approx_tokens'])}")
print(f"Après / requête                     : {format_number(avg_after_tokens)}")
print(f"Réduction globale                   : {global_tokens_reduction:.2f} %")
print()

print("=" * 80)
print("IMPORTANT")
print("=" * 80)
print()
print(
    "Les tokens affichés sont une approximation basée sur ~4 caractères/token."
)
print(
    "Ils servent à comparer AVANT / APRÈS, pas à reproduire le tokenizer exact."
)
print()