import os
import time

from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def call(label, messages):
    print("\n" + "=" * 70)
    print(label)
    print("=" * 70)

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=128,
        temperature=0.2,
        tool_choice="none",
    )

    elapsed = time.perf_counter() - start

    print(f"Temps : {elapsed:.3f}s")
    print("Finish :", response.choices[0].finish_reason)
    print("Réponse :", repr(response.choices[0].message.content))

    return elapsed


PROMPT = (
    SYSTEM_PROMPT
    + "\n\nIMPORTANT POUR CE TEST : "
      "n'utilise aucun outil et ne demande aucun outil. "
      "Réponds directement avec tes connaissances."
)


# ---------------------------------------------------------
# TEST 1 — 2 messages
# ---------------------------------------------------------

messages_1 = [
    {"role": "system", "content": PROMPT},
    {
        "role": "user",
        "content": "Quel est le nom de la planète sur laquelle nous vivons ?"
    },
]

t1 = call(
    "TEST 1 — 2 messages",
    messages_1,
)


# ---------------------------------------------------------
# TEST 2 — conversation multi-tour + system
# ---------------------------------------------------------

messages_2 = [
    {"role": "system", "content": PROMPT},
    {
        "role": "user",
        "content": "Bonjour."
    },
    {
        "role": "assistant",
        "content": "Bonjour ! Comment puis-je t'aider ?"
    },
    {
        "role": "user",
        "content": "Sur quelle planète vivons-nous ?"
    },
]

t2 = call(
    "TEST 2 — 4 messages + system",
    messages_2,
)


# ---------------------------------------------------------
# TEST 3 — plusieurs messages sans system
# ---------------------------------------------------------

messages_3 = [
    {
        "role": "user",
        "content": "Bonjour."
    },
    {
        "role": "assistant",
        "content": "Bonjour !"
    },
    {
        "role": "user",
        "content": "Comment vas-tu ?"
    },
    {
        "role": "assistant",
        "content": "Je vais bien."
    },
    {
        "role": "user",
        "content": "Sur quelle planète vivons-nous ?"
    },
]

t3 = call(
    "TEST 3 — 5 messages sans system",
    messages_3,
)


# ---------------------------------------------------------
# RÉSULTATS
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("RÉSULTATS")
print("=" * 70)

print(f"TEST 1 — 2 messages              : {t1:.3f}s")
print(f"TEST 2 — 4 messages + system     : {t2:.3f}s")
print(f"TEST 3 — 5 messages sans system  : {t3:.3f}s")

print("=" * 70)