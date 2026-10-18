import os
import time

from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL

load_dotenv()

print("=" * 60)
print("AMAH — BENCHMARK LLM CONTEXTE PROPRE")
print("=" * 60)

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise SystemExit("GROQ_API_KEY introuvable")

client = Groq(api_key=api_key)


def test_llm(label, messages):
    print("\n" + "-" * 60)
    print(label)

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=256,
        temperature=0.2,
    )

    elapsed = time.perf_counter() - start

    print(f"Temps : {elapsed:.3f}s")
    print("Finish reason :", response.choices[0].finish_reason)
    print("Réponse :", response.choices[0].message.content)

    return elapsed


# ==================================================
# TEST 1 — contexte normal
# ==================================================

messages_1 = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    },
    {
        "role": "user",
        "content": (
            "Réponds simplement : "
            "quelle est la capitale de la Guinée ? "
            "N'utilise aucun outil."
        )
    }
]

t1 = test_llm(
    "TEST 1 — contexte initial",
    messages_1
)


# ==================================================
# TEST 2 — contexte artificiellement augmenté
# ==================================================

messages_2 = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    },
    {
        "role": "user",
        "content": (
            "Voici des informations déjà obtenues : "
            "la météo de Conakry est de 25°C avec des averses légères. "
            "Un calcul précédent a donné 9250000. "
            "La date actuelle est le 28/09/2026. "
            "Réponds simplement : "
            "quelle est la capitale de la Guinée ? "
            "N'utilise aucun outil."
        )
    }
]

t2 = test_llm(
    "TEST 2 — contexte enrichi",
    messages_2
)


print("\n" + "=" * 60)
print("RÉSULTATS")
print("=" * 60)

print(f"\nTEST 1 : {t1:.3f}s")
print(f"TEST 2 : {t2:.3f}s")
print(f"Différence : {t2 - t1:+.3f}s")

print("\n" + "=" * 60)
print("FIN DU BENCHMARK")
print("=" * 60)