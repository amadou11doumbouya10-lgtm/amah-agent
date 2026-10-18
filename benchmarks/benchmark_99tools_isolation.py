import os
import time
from dotenv import load_dotenv
from groq import Groq
from config import TOOLS_DEFINITIONS

load_dotenv()

MODEL = os.getenv("MODEL", "openai/gpt-oss-120b")
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError("GROQ_API_KEY manquante")

client = Groq(api_key=API_KEY)

messages = [
    {
        "role": "system",
        "content": "Tu es Amah. Réponds simplement et brièvement."
    },
    {
        "role": "user",
        "content": "Dis simplement : bonjour."
    }
]

print("=" * 70)
print("BENCHMARK — 99 OUTILS ISOLATION")
print("=" * 70)
print(f"MODEL : {MODEL}")
print(f"TOOLS : {len(TOOLS_DEFINITIONS)}")
print("=" * 70)

results = []

for i in range(1, 7):

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS_DEFINITIONS,
        tool_choice="none",
        max_tokens=256,
        temperature=0.2,
    )

    elapsed = time.perf_counter() - start
    results.append(elapsed)

    choice = response.choices[0]
    usage = response.usage

    print(f"\nTEST {i}/6")
    print(f"Temps             : {elapsed:.3f}s")
    print(f"Finish reason     : {choice.finish_reason}")
    print(f"Prompt tokens     : {usage.prompt_tokens}")
    print(f"Completion tokens : {usage.completion_tokens}")
    print(f"Total tokens      : {usage.total_tokens}")
    print(f"Réponse           : {choice.message.content!r}")

print("\n" + "=" * 70)
print("RÉSUMÉ")
print("=" * 70)

print(f"Minimum : {min(results):.3f}s")
print(f"Maximum : {max(results):.3f}s")
print(f"Moyenne : {sum(results)/len(results):.3f}s")