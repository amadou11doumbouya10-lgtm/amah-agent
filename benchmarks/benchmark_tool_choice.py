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

MAX_TOKENS = 512
REPETITIONS = 3


def llm_call(messages, tool_choice):
    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS_DEFINITIONS,
        tool_choice=tool_choice,
        max_tokens=MAX_TOKENS,
        temperature=0.4,
    )

    elapsed = time.perf_counter() - start
    return response, elapsed


def execute_weather(tool_call):
    name = tool_call.function.name

    try:
        args = json.loads(tool_call.function.arguments or "{}")
    except Exception:
        args = {}

    func = TOOL_FUNCTIONS.get(name)

    if not func:
        return {
            "error": f"Outil inconnu: {name}"
        }

    try:
        return func(**args)
    except Exception as e:
        return {
            "error": str(e)
        }


def run_test(label, final_tool_choice):
    print()
    print("=" * 78)
    print(label)
    print(f"Deuxième appel : tool_choice={final_tool_choice}")
    print("=" * 78)

    times = []

    for repetition in range(1, REPETITIONS + 1):

        print()
        print(f"--- Répétition {repetition}/{REPETITIONS} ---")

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": "Donne-moi la météo actuelle à Conakry.",
            },
        ]

        # =====================================================
        # APPEL 1 : DEMANDE DE L'OUTIL
        # =====================================================

        try:
            response1, time1 = llm_call(messages, "auto")

            choice1 = response1.choices[0]
            msg1 = choice1.message

            print(f"LLM #1 : {time1:.3f}s")
            print(f"Finish : {choice1.finish_reason}")
            print(f"Tool calls : {len(msg1.tool_calls or [])}")

            if not msg1.tool_calls:
                print("⚠️ Aucun tool call.")
                continue

            # Même structure que agent.py
            messages.append({
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
            })

            # =================================================
            # EXÉCUTION OUTIL
            # =================================================

            for tool_call in msg1.tool_calls:

                print(f"Outil : {tool_call.function.name}")

                start_tool = time.perf_counter()

                result = execute_weather(tool_call)

                tool_time = time.perf_counter() - start_tool

                print(f"Temps outil : {tool_time:.3f}s")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        result,
                        ensure_ascii=False,
                        default=str,
                    ),
                })

            # =================================================
            # APPEL 2 : TEST AUTO OU NONE
            # =================================================

            start2 = time.perf_counter()

            response2 = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS_DEFINITIONS,
                tool_choice=final_tool_choice,
                max_tokens=MAX_TOKENS,
                temperature=0.4,
            )

            time2 = time.perf_counter() - start2

            choice2 = response2.choices[0]
            msg2 = choice2.message

            usage2 = response2.usage

            print(f"LLM #2 : {time2:.3f}s")
            print(f"Finish : {choice2.finish_reason}")
            print(f"Tool calls supplémentaires : {len(msg2.tool_calls or [])}")
            print(
                f"Tokens : "
                f"{usage2.prompt_tokens} prompt / "
                f"{usage2.completion_tokens} completion / "
                f"{usage2.total_tokens} total"
            )
            print(f"Réponse : {(msg2.content or '')[:300]!r}")

            times.append(time2)

        except Exception as e:
            print()
            print("❌ ERREUR")
            print(type(e).__name__, ":", e)

    if times:
        print()
        print(
            f"Temps LLM #2 : "
            f"min={min(times):.3f}s | "
            f"max={max(times):.3f}s | "
            f"moyenne={sum(times)/len(times):.3f}s"
        )

    return times


print()
print("=" * 78)
print("BENCHMARK A/B — TOOL_CHOICE APRÈS EXÉCUTION D'UN OUTIL")
print("=" * 78)
print(f"MODEL : {MODEL}")
print(f"OUTILS : {len(TOOL_FUNCTIONS)}")
print(f"MAX_TOKENS : {MAX_TOKENS}")
print(f"RÉPÉTITIONS : {REPETITIONS}")
print("=" * 78)

# TEST A : comportement actuel d'Amah
times_auto = run_test(
    "TEST A — COMPORTEMENT ACTUEL",
    "auto",
)

# TEST B : on force une réponse finale
times_none = run_test(
    "TEST B — RÉPONSE FINALE FORCÉE",
    "none",
)

# =============================================================
# COMPARAISON
# =============================================================

print()
print()
print("=" * 78)
print("COMPARAISON FINALE")
print("=" * 78)

print(
    f"{'Mode':<20} | "
    f"{'Min':>8} | "
    f"{'Moyenne':>10} | "
    f"{'Max':>8}"
)

print("-" * 55)

if times_auto:
    print(
        f"{'AUTO':<20} | "
        f"{min(times_auto):>7.3f}s | "
        f"{sum(times_auto)/len(times_auto):>9.3f}s | "
        f"{max(times_auto):>7.3f}s"
    )

if times_none:
    print(
        f"{'NONE':<20} | "
        f"{min(times_none):>7.3f}s | "
        f"{sum(times_none)/len(times_none):>9.3f}s | "
        f"{max(times_none):>7.3f}s"
    )

print("=" * 78)