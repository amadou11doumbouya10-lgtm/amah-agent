import os
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = os.getenv("MODEL", "openai/gpt-oss-120b")
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError("GROQ_API_KEY manquante dans .env")

client = Groq(api_key=API_KEY)

PROMPT = "Réponds simplement : quelle est la capitale de la Guinée ?"

print("=" * 70)
print("BENCHMARK — VARIABILITÉ DU MODÈLE")
print("=" * 70)
print(f"MODEL       : {MODEL}")
print("TOOLS       : aucune")
print("TOOL CHOICE : none")
print("MAX TOKENS  : 256")
print("TEMPERATURE : 0.2")
print("=" * 70)

results = []

for i in range(1, 7):
    print(f"\n--- TEST {i}/6 ---")

    start = time.perf_counter()

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT
                }
            ],
            tools=[],
            tool_choice="none",
            max_tokens=256,
            temperature=0.2,
        )

        elapsed = time.perf_counter() - start

        choice = response.choices[0]
        usage = response.usage

        finish = choice.finish_reason
        content = choice.message.content or ""

        prompt_tokens = getattr(usage, "prompt_tokens", 0)
        completion_tokens = getattr(usage, "completion_tokens", 0)
        total_tokens = getattr(usage, "total_tokens", 0)

        results.append(elapsed)

        print(f"Temps            : {elapsed:.3f}s")
        print(f"Finish reason    : {finish}")
        print(f"Prompt tokens    : {prompt_tokens}")
        print(f"Completion tokens: {completion_tokens}")
        print(f"Total tokens     : {total_tokens}")
        print(f"Réponse          : {content!r}")

    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"ERREUR après {elapsed:.3f}s : {e}")

print("\n" + "=" * 70)
print("RÉSUMÉ")
print("=" * 70)

if results:
    print(f"Nombre de tests : {len(results)}")
    print(f"Minimum         : {min(results):.3f}s")
    print(f"Maximum         : {max(results):.3f}s")
    print(f"Moyenne         : {sum(results)/len(results):.3f}s")

    print("\nTemps individuels :")
    for i, t in enumerate(results, 1):
        print(f"  Test {i}: {t:.3f}s")