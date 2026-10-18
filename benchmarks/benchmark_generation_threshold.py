import os
import time
from groq import Groq
from dotenv import load_dotenv
from config import SYSTEM_PROMPT, MODEL

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY manquante dans .env")

client = Groq(api_key=api_key)

PROMPT = SYSTEM_PROMPT + """
IMPORTANT :
n'utilise aucun outil.
Réponds directement à l'utilisateur.
"""

messages = [
    {"role": "system", "content": PROMPT},
    {"role": "user", "content": "Donne-moi une information simple."},
    {"role": "assistant", "content": "Voici une information."},
    {"role": "user", "content": "Résultat : 25, 10, 37, 100, 2026."},
]

TESTS = [
    64,
    128,
    192,
    256,
    320,
    384,
    448,
    512,
    640,
    768,
    1024,
    1536,
    2048,
]

print()
print("=" * 75)
print("BENCHMARK — SEUIL DE GENERATION")
print("=" * 75)
print(f"MODEL : {MODEL}")
print("=" * 75)
print()

results = []

for max_tokens in TESTS:
    print(f"TEST max_tokens={max_tokens}")
    print("-" * 75)

    start = time.perf_counter()

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2,
            tool_choice="none",
        )

        elapsed = time.perf_counter() - start

        choice = response.choices[0]
        usage = response.usage

        prompt_tokens = getattr(usage, "prompt_tokens", "?")
        completion_tokens = getattr(usage, "completion_tokens", "?")
        total_tokens = getattr(usage, "total_tokens", "?")

        finish_reason = choice.finish_reason
        content = choice.message.content or ""

        results.append({
            "max_tokens": max_tokens,
            "time": elapsed,
            "completion": completion_tokens,
            "total": total_tokens,
            "finish": finish_reason,
        })

        print(f"Temps              : {elapsed:.3f}s")
        print(f"Finish reason      : {finish_reason}")
        print(f"Prompt tokens      : {prompt_tokens}")
        print(f"Completion tokens  : {completion_tokens}")
        print(f"Total tokens       : {total_tokens}")
        print(f"Réponse            : {content[:180]!r}")

    except Exception as e:
        elapsed = time.perf_counter() - start

        results.append({
            "max_tokens": max_tokens,
            "time": elapsed,
            "completion": "ERROR",
            "total": "ERROR",
            "finish": "ERROR",
        })

        print(f"ERREUR après {elapsed:.3f}s")
        print(type(e).__name__, ":", e)

    print()

print()
print("=" * 75)
print("RÉSULTATS FINAUX")
print("=" * 75)

print(
    f"{'max_tokens':>12} | "
    f"{'temps':>10} | "
    f"{'completion':>12} | "
    f"{'finish':>10}"
)
print("-" * 55)

for r in results:
    print(
        f"{r['max_tokens']:>12} | "
        f"{r['time']:>9.3f}s | "
        f"{str(r['completion']):>12} | "
        f"{str(r['finish']):>10}"
    )

print("=" * 75)