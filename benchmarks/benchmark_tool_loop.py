import os
import time
import json

from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise SystemExit("GROQ_API_KEY introuvable")

client = Groq(api_key=api_key)


def call(label, messages):
    print("\n" + "=" * 60)
    print(label)
    print("=" * 60)

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS_DEFINITIONS,
        tool_choice="auto",
        max_tokens=256,
        temperature=0.2,
    )

    elapsed = time.perf_counter() - start

    msg = response.choices[0].message

    print(f"Temps : {elapsed:.3f}s")
    print("Finish :", response.choices[0].finish_reason)
    print("Content :", repr(msg.content))
    print("Tool calls :", msg.tool_calls)

    return response, elapsed


# ---------------------------------------------------------
# TEST 1 — appel normal avec outils disponibles
# ---------------------------------------------------------

messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {
        "role": "user",
        "content": "Dis-moi simplement bonjour."
    }
]

r1, t1 = call("TEST 1 — LLM normal + outils disponibles", messages)


# ---------------------------------------------------------
# TEST 2 — simulation d'un tool call
# ---------------------------------------------------------

messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {
        "role": "user",
        "content": "Quelle est la météo actuelle à Conakry ?"
    }
]

r2, t2 = call("TEST 2 — demande nécessitant un outil", messages)


# ---------------------------------------------------------
# Si le modèle a réellement appelé un outil,
# on ajoute exactement son message assistant + résultat outil.
# ---------------------------------------------------------

if r2.choices[0].message.tool_calls:

    msg = r2.choices[0].message

    tool_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "Quelle est la météo actuelle à Conakry ?"
        },
        {
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        },
    ]

    # On simule le résultat du tool
    for tc in msg.tool_calls:
        tool_messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps({
                "temperature": 25,
                "condition": "averses légères",
                "city": "Conakry"
            })
        })

    r3, t3 = call(
        "TEST 3 — APRÈS TOOL CALL",
        tool_messages
    )

    print("\n" + "=" * 60)
    print("RÉSULTAT")
    print("=" * 60)
    print(f"Test 1 : {t1:.3f}s")
    print(f"Test 2 : {t2:.3f}s")
    print(f"Test 3 : {t3:.3f}s")
    print("=" * 60)

else:
    print("\n⚠️ Le modèle n'a pas produit de tool call au TEST 2.")