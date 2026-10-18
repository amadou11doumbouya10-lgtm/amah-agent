import os
import time

from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PROMPT = SYSTEM_PROMPT + """
IMPORTANT :
n'utilise aucun outil.
Réponds directement.
"""


def run(label, messages, max_tokens):
    print("\n" + "=" * 70)
    print(label)
    print("=" * 70)

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.2,
        tool_choice="none",
    )

    elapsed = time.perf_counter() - start

    usage = response.usage

    print(f"Temps : {elapsed:.3f}s")
    print("Finish :", response.choices[0].finish_reason)
    print("Réponse :", repr(response.choices[0].message.content))

    if usage:
        print("Prompt tokens :", usage.prompt_tokens)
        print("Completion tokens :", usage.completion_tokens)
        print("Total tokens :", usage.total_tokens)

    return elapsed


messages = [
    {"role": "system", "content": PROMPT},
    {
        "role": "user",
        "content": "Donne-moi une information simple."
    },
    {
        "role": "assistant",
        "content": "Voici une information."
    },
    {
        "role": "user",
        "content": "Résultat : 25, 10, 37, 100, 2026."
    },
]


print("\nMODEL :", MODEL)

# ---------------------------------------------------------
# TEST 1 — 128 tokens
# ---------------------------------------------------------

t1 = run(
    "TEST 1 — max_tokens=128",
    messages,
    128,
)


# ---------------------------------------------------------
# TEST 2 — 256 tokens
# ---------------------------------------------------------

t2 = run(
    "TEST 2 — max_tokens=256",
    messages,
    256,
)


# ---------------------------------------------------------
# TEST 3 — 512 tokens
# ---------------------------------------------------------

t3 = run(
    "TEST 3 — max_tokens=512",
    messages,
    512,
)


print("\n" + "=" * 70)
print("RÉSULTATS")
print("=" * 70)

print(f"128 tokens : {t1:.3f}s")
print(f"256 tokens : {t2:.3f}s")
print(f"512 tokens : {t3:.3f}s")

print("=" * 70)