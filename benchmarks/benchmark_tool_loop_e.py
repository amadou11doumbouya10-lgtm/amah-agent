import os
import time

from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def run(label, messages):
    print("\n" + "=" * 70)
    print(label)
    print("=" * 70)

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

    print(f"Temps : {elapsed:.3f}s")
    print("Finish :", response.choices[0].finish_reason)
    print("Réponse :", repr(response.choices[0].message.content))

    return elapsed


base = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {
        "role": "user",
        "content": "Quelle est la météo actuelle à Conakry ?"
    },
]


# ---------------------------------------------------------
# Obtenir le tool call
# ---------------------------------------------------------

response = client.chat.completions.create(
    model=MODEL,
    messages=base,
    tools=TOOLS_DEFINITIONS,
    tool_choice="auto",
    max_tokens=256,
    temperature=0.2,
)

msg = response.choices[0].message

print("Tool call obtenu :", msg.tool_calls)


# ---------------------------------------------------------
# TEST E1
# Même conversation MAIS on transforme le tool_call
# en texte normal dans le message assistant.
# ---------------------------------------------------------

messages_e1 = base + [
    {
        "role": "assistant",
        "content": (
            "J'ai utilisé get_weather avec "
            '{"location":"Conakry"}.'
        ),
    },
    {
        "role": "user",
        "content": (
            "Résultat : "
            '{"temperature":25,"condition":"averses légères"}'
        ),
    },
]

t1 = run(
    "TEST E1 — historique textuel sans tool_calls",
    messages_e1,
)


# ---------------------------------------------------------
# TEST E2
# Même message assistant avec tool_calls,
# MAIS sans résultat supplémentaire.
# ---------------------------------------------------------

if msg.tool_calls:

    tc = msg.tool_calls[0]

    assistant_tool_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
        ],
    }

    messages_e2 = base + [
        assistant_tool_message
    ]

    t2 = run(
        "TEST E2 — tool_calls sans résultat",
        messages_e2,
    )

    print("\n" + "=" * 70)
    print("COMPARAISON")
    print("=" * 70)
    print(f"E1 — historique texte : {t1:.3f}s")
    print(f"E2 — tool_calls       : {t2:.3f}s")
    print("=" * 70)