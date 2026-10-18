"""
Amah Agent - Benchmark Context Profiles

Mesure le poids de l'historique selon différents niveaux
de conservation.

Aucun appel Groq.
Aucun tool exécuté.
"""

from config import SYSTEM_PROMPT
from tools.memory import load_recent_messages


def approximate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def serialize_messages(messages) -> str:
    return str(messages)


# Historique disponible
history = load_recent_messages(limit=40)

# Profils à comparer
PROFILES = [
    40,
    30,
    20,
    15,
    10,
    5,
    0,
]


system_chars = len(SYSTEM_PROMPT)
system_tokens = approximate_tokens(SYSTEM_PROMPT)


print()
print("=" * 90)
print("AMAH — BENCHMARK DES PROFILS DE CONTEXTE")
print("=" * 90)

print()
print(f"Historique disponible : {len(history)} messages")
print(f"System prompt         : {system_chars:,} caractères")
print(f"System prompt         : {system_tokens:,} tokens approx.")

print()


for limit in PROFILES:

    selected_history = history[-limit:] if limit > 0 else []

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *selected_history,
    ]

    history_text = serialize_messages(selected_history)
    all_text = serialize_messages(messages)

    history_chars = len(history_text)
    history_tokens = approximate_tokens(history_text)

    total_chars = len(all_text)
    total_tokens = approximate_tokens(all_text)

    print("-" * 90)

    print(f"PROFIL : {limit} messages")

    print()
    print(f"Historique     : {history_chars:,} caractères")
    print(f"Historique     : {history_tokens:,} tokens approx.")

    print()
    print(f"Total contexte : {total_chars:,} caractères")
    print(f"Total contexte : {total_tokens:,} tokens approx.")

    print()


print("=" * 90)
print("FIN DU BENCHMARK")
print("=" * 90)
print()