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


# Obtenir le tool call
response = client.chat.completions.create(
    model=MODEL,
    messages=base,
    tools=TOOLS_DEFINITIONS,
    tool_choice="auto",
    max_tokens=256,
    temperature=0.2,
)

msg = response.choices[0].message
tc = msg.tool_calls[0]

assistant_message = {
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
    ],
}


# ---------------------------------------------------------
# TEST D
# On garde l'assistant tool_call,
# mais on transforme le résultat du tool en USER.
# ---------------------------------------------------------

messages = base + [
    assistant_message,
    {
        "role": "user",
        "content": (
            "Résultat de get_weather : "
            '{"temperature":25,"condition":"averses légères"}'
        ),
    },
]

run(
    "TEST D — assistant tool_call + résultat en USER",
    messages,
)