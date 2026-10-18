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

counts = [0, 10, 20, 40, 60, 80, 99]

print("=" * 70)
print("BENCHMARK — IMPACT DU NOMBRE D'OUTILS")
print("=" * 70)
print(f"MODEL : {MODEL}")
print(f"OUTILS DISPONIBLES : {len(TOOLS_DEFINITIONS)}")
print("=" * 70)

for count in counts:

    tools = TOOLS_DEFINITIONS[:count]

    print(f"\n{'-' * 70}")
    print(f"TEST AVEC {count} OUTILS")
    print(f"{'-' * 70}")

    times = []

    for rep in range(1, 4):

        start = time.perf_counter()

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="none",
            max_tokens=256,
            temperature=0.2,
        )

        elapsed = time.perf_counter() - start
        times.append(elapsed)

        usage = response.usage

        print(
            f"  Rep {rep}: "
            f"{elapsed:.3f}s | "
            f"prompt={usage.prompt_tokens} | "
            f"completion={usage.completion_tokens}"
        )

    print(
        f"  → min={min(times):.3f}s | "
        f"max={max(times):.3f}s | "
        f"moyenne={sum(times)/len(times):.3f}s"
    )

print("\n" + "=" * 70)
print("FIN DU BENCHMARK")
print("=" * 70)