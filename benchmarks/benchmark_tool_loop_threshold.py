import os
import time
import json
from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS
from tools import TOOL_FUNCTIONS

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY manquante dans .env")

client = Groq(api_key=api_key)

LOCATION = "Conakry"

TESTS = [256, 512, 1024, 1536, 2048]


def call_llm(messages, max_tokens):
    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS_DEFINITIONS,
        tool_choice="auto",
        max_tokens=max_tokens,
        temperature=0.4,
    )

    elapsed = time.perf_counter() - start
    return response, elapsed


print()
print("=" * 78)
print("BENCHMARK — VRAI CYCLE TOOL CALL D'AMAH")
print("=" * 78)
print(f"MODEL : {MODEL}")
print(f"OUTILS : {len(TOOL_FUNCTIONS)}")
print("=" * 78)
print()

results = []


for max_tokens in TESTS:

    print()
    print("=" * 78)
    print(f"TEST max_tokens={max_tokens}")
    print("=" * 78)

    # ---------------------------------------------------------
    # APPEL 1 : Amah reçoit la demande et doit appeler météo
    # ---------------------------------------------------------

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "Donne-moi la météo actuelle à Conakry, "
                "puis calcule 250000 * 37 et donne-moi la date et l'heure actuelles."
            ),
        },
    ]

    try:
        response1, time1 = call_llm(messages, max_tokens)

        choice1 = response1.choices[0]
        msg1 = choice1.message

        print(f"\nLLM #1 : {time1:.3f}s")
        print(f"Finish  : {choice1.finish_reason}")
        print(f"Tool calls : {len(msg1.tool_calls or [])}")

        usage1 = response1.usage

        print(
            f"Tokens : "
            f"{usage1.prompt_tokens} prompt / "
            f"{usage1.completion_tokens} completion / "
            f"{usage1.total_tokens} total"
        )

        if not msg1.tool_calls:
            print("⚠️ Aucun tool call généré.")
            continue

        # Ajouter le message assistant exactement comme agent.py
        assistant_message = {
            "role": "assistant",
            "content": msg1.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg1.tool_calls
            ],
        }

        messages.append(assistant_message)

        # ---------------------------------------------------------
        # EXÉCUTION DES OUTILS
        # ---------------------------------------------------------

        for tool_call in msg1.tool_calls:

            name = tool_call.function.name

            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except Exception:
                args = {}

            print(f"\nOUTIL : {name}")
            print(f"ARGS  : {args}")

            tool_start = time.perf_counter()

            func = TOOL_FUNCTIONS.get(name)

            if not func:
                result = {
                    "error": f"Outil inconnu: {name}"
                }
            else:
                try:
                    result = func(**args)
                except Exception as e:
                    result = {
                        "error": str(e)
                    }

            tool_time = time.perf_counter() - tool_start

            print(f"Temps outil : {tool_time:.3f}s")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        result,
                        ensure_ascii=False,
                        default=str,
                    ),
                }
            )

        # ---------------------------------------------------------
        # APPEL 2 : C'EST CELUI QUI NOUS INTÉRESSE
        # ---------------------------------------------------------

        print()
        print(">>> APPEL LLM #2 APRÈS LES OUTILS <<<")

        response2, time2 = call_llm(messages, max_tokens)

        choice2 = response2.choices[0]
        msg2 = choice2.message

        usage2 = response2.usage

        print(f"\nLLM #2 : {time2:.3f}s")
        print(f"Finish  : {choice2.finish_reason}")
        print(f"Tool calls supplémentaires : {len(msg2.tool_calls or [])}")

        print(
            f"Tokens : "
            f"{usage2.prompt_tokens} prompt / "
            f"{usage2.completion_tokens} completion / "
            f"{usage2.total_tokens} total"
        )

        print(f"Réponse : {(msg2.content or '')[:300]!r}")

        results.append(
            {
                "max_tokens": max_tokens,
                "llm1": time1,
                "llm2": time2,
                "prompt_tokens": usage2.prompt_tokens,
                "completion_tokens": usage2.completion_tokens,
                "finish": choice2.finish_reason,
            }
        )

    except Exception as e:

        print()
        print("❌ ERREUR")
        print(type(e).__name__, ":", e)


# =============================================================
# RÉSULTATS
# =============================================================

print()
print()
print("=" * 78)
print("RÉSULTATS FINAUX")
print("=" * 78)

print(
    f"{'max_tokens':>12} | "
    f"{'LLM #1':>10} | "
    f"{'LLM #2':>10} | "
    f"{'prompt':>8} | "
    f"{'completion':>10} | "
    f"{'finish':>8}"
)

print("-" * 78)

for r in results:

    print(
        f"{r['max_tokens']:>12} | "
        f"{r['llm1']:>9.3f}s | "
        f"{r['llm2']:>9.3f}s | "
        f"{r['prompt_tokens']:>8} | "
        f"{r['completion_tokens']:>10} | "
        f"{r['finish']:>8}"
    )

print("=" * 78)