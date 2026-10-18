import os
import time
from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS
from tools import TOOL_FUNCTIONS
from tools.memory import load_recent_messages

load_dotenv()

print("=" * 60)
print("AMAH AGENT — BENCHMARK PIPELINE RÉEL")
print("=" * 60)

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("ERREUR : GROQ_API_KEY introuvable")
    raise SystemExit(1)

client = Groq(api_key=api_key)

messages = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

# --------------------------------------------------
# Demande complexe
# --------------------------------------------------

user_input = (
    "Donne-moi la météo actuelle à Conakry, "
    "calcule 250000 multiplié par 37, "
    "puis donne-moi la date et l'heure actuelles."
)

messages.append({
    "role": "user",
    "content": user_input
})

print("\n[USER]")
print(user_input)

# --------------------------------------------------
# Appels LLM + outils
# --------------------------------------------------

total_start = time.perf_counter()
llm_calls = 0
tool_calls = 0
tool_time = 0

while True:

    print("\n" + "-" * 60)

    llm_calls += 1

    print(f"[LLM #{llm_calls}] Appel...")

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS_DEFINITIONS,
        tool_choice="auto",
        max_tokens=2048,
        temperature=0.4,
    )

    elapsed = time.perf_counter() - start

    print(f"[PERF] LLM #{llm_calls}: {elapsed:.3f}s")

    msg = response.choices[0].message

    print(f"[INFO] finish_reason: {response.choices[0].finish_reason}")

    if not msg.tool_calls:
        print("\n[FINAL]")
        print(msg.content)
        break

    print(f"[INFO] Nombre d'outils demandés : {len(msg.tool_calls)}")

    # Ajouter le message assistant
    messages.append({
        "role": "assistant",
        "content": msg.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in msg.tool_calls
        ]
    })

    # --------------------------------------------------
    # Exécution des outils
    # --------------------------------------------------

    for tool_call in msg.tool_calls:

        name = tool_call.function.name

        try:
            import json
            args = json.loads(tool_call.function.arguments) or {}
        except Exception:
            args = {}

        func = TOOL_FUNCTIONS.get(name)

        print(f"\n[TOOL #{tool_calls + 1}] {name}")
        print(f"[ARGS] {args}")

        if not func:
            result = {
                "error": f"Outil inconnu: {name}"
            }
        else:

            tool_calls += 1

            start = time.perf_counter()

            try:
                result = func(**args)
            except Exception as e:
                result = {
                    "error": str(e)
                }

            elapsed = time.perf_counter() - start

            tool_time += elapsed

            print(f"[PERF] {name}: {elapsed:.3f}s")

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": __import__("json").dumps(
                result,
                ensure_ascii=False,
                default=str
            )
        })

# --------------------------------------------------
# Résultats
# --------------------------------------------------

total_time = time.perf_counter() - total_start

print("\n" + "=" * 60)
print("RÉSULTATS FINAUX")
print("=" * 60)

print(f"\nNombre d'appels LLM : {llm_calls}")
print(f"Nombre d'outils     : {tool_calls}")
print(f"Temps outils        : {tool_time:.3f}s")
print(f"Temps TOTAL         : {total_time:.3f}s")

print("\n" + "=" * 60)
print("BENCHMARK TERMINÉ")
print("=" * 60)