import os
import time

from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PROMPT = SYSTEM_PROMPT + """
IMPORTANT POUR CE TEST :
n'utilise aucun outil.
Réponds directement.
"""


def test(label, messages):
    print("\n" + "=" * 70)
    print(label)
    print("=" * 70)

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=256,
        temperature=0.2,
        tool_choice="none",
    )

    elapsed = time.perf_counter() - start

    print(f"Temps : {elapsed:.3f}s")
    print("Finish :", response.choices[0].finish_reason)
    print("Réponse :", repr(response.choices[0].message.content))

    return elapsed


# =========================================================
# TEST A — météo, mais conversation normale
# =========================================================

messages_a = [
    {"role": "system", "content": PROMPT},
    {
        "role": "user",
        "content": "Quelle est la météo actuelle à Conakry ?"
    },
    {
        "role": "assistant",
        "content": "Je vais vérifier la météo de Conakry."
    },
    {
        "role": "user",
        "content": (
            "Résultat : "
            '{"temperature":25,"condition":"averses légères"}'
        )
    },
]

ta = test(
    "TEST A — météo + historique",
    messages_a,
)


# =========================================================
# TEST B — contenu neutre
# =========================================================

messages_b = [
    {"role": "system", "content": PROMPT},
    {
        "role": "user",
        "content": "Quelle est la couleur du ciel ?"
    },
    {
        "role": "assistant",
        "content": "Je vais répondre à ta question."
    },
    {
        "role": "user",
        "content": "Résultat : le ciel est généralement bleu."
    },
]

tb = test(
    "TEST B — conversation neutre",
    messages_b,
)


# =========================================================
# TEST C — même longueur approximative, nombres uniquement
# =========================================================

messages_c = [
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

tc = test(
    "TEST C — chiffres",
    messages_c,
)


print("\n" + "=" * 70)
print("RÉSULTATS")
print("=" * 70)

print(f"TEST A météo   : {ta:.3f}s")
print(f"TEST B neutre  : {tb:.3f}s")
print(f"TEST C chiffres: {tc:.3f}s")

print("=" * 70)