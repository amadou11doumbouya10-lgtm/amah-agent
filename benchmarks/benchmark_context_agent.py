from config import SYSTEM_PROMPT, TOOLS_DEFINITIONS
from tools.memory import load_recent_messages
from tools.router_v03 import route_tools


def approximate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def serialize_messages(messages) -> str:
    return str(messages)


previous = load_recent_messages(limit=40)

messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    *previous,
]

tests = [
    "Salut Amah",
    "Quelle est la météo à Conakry ?",
    "Calcule 250000 * 37",
]

print("=" * 80)
print("AMAH — ANALYSE DU CONTEXTE")
print("=" * 80)

print()
print(f"Messages historiques : {len(previous)}")
print(f"Messages totaux     : {len(messages)}")

system_text = SYSTEM_PROMPT
history_text = serialize_messages(previous)
all_text = serialize_messages(messages)

print()
print("SYSTEM PROMPT")
print(f"  caractères : {len(system_text):,}")
print(f"  tokens ≈   : {approximate_tokens(system_text):,}")

print()
print("HISTORIQUE")
print(f"  caractères : {len(history_text):,}")
print(f"  tokens ≈   : {approximate_tokens(history_text):,}")

print()
print("SYSTEM + HISTORIQUE")
print(f"  caractères : {len(all_text):,}")
print(f"  tokens ≈   : {approximate_tokens(all_text):,}")

print()

for text in tests:

    selected, intents = route_tools(
        text,
        TOOLS_DEFINITIONS,
        max_tools=12,
    )

    tools_text = str(selected)

    print("=" * 80)
    print(f"DEMANDE : {text}")
    print(f"INTENTIONS : {intents}")
    print(f"OUTILS : {len(selected)}")
    print(f"TOOLS chars : {len(tools_text):,}")
    print(f"TOOLS tokens ≈ : {approximate_tokens(tools_text):,}")

print()
print("=" * 80)