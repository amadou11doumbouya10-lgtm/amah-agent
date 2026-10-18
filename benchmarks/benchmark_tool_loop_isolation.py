import os
import time

from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise SystemExit("GROQ_API_KEY introuvable")

client = Groq(api_key=api_key)


def run_test(label, messages, use_tools=True):
    print("\n" + "=" * 70)
    print(label)
    print("=" * 70)

    start = time.perf_counter()

    kwargs = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 256,
        "temperature": 0.2,
    }

    if use_tools:
        kwargs["tools"] = TOOLS_DEFINITIONS
        kwargs["tool_choice"] = "auto"

    response = client.chat.completions.create(**kwargs)

    elapsed = time.perf_counter() - start

    print(f"Temps : {elapsed:.3f}s")
    print("Finish :", response.choices[0].finish_reason)
    print("Réponse :", repr(response.choices[0].message.content))

    return elapsed


# ---------------------------------------------------------
# BASE
# ---------------------------------------------------------

base = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {
        "role": "user",
        "content": "Quelle est la météo actuelle à Conakry ?"
    },
]


# ---------------------------------------------------------
# ÉTAPE 1 : obtenir le tool call
# ---------------------------------------------------------

print("\nObtention du tool call...")

response = client.chat.completions.create(
    model=MODEL,
    messages=base,
    tools=TOOLS_DEFINITIONS,
    tool_choice="auto",
    max_tokens=256,
    temperature=0.2,
)

msg = response.choices[0].message

print("Tool calls :", msg.tool_calls)

if not msg.tool_calls:
    raise SystemExit("Le modèle n'a pas produit de tool call.")


tc = msg.tool_calls[0]


# ---------------------------------------------------------
# MESSAGE ASSISTANT EXACT
# ---------------------------------------------------------

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
# TEST A
# assistant + tool result
# + TOOLS
# ---------------------------------------------------------

messages_a = base + [
    assistant_message,
    {
        "role": "tool",
        "tool_call_id": tc.id,
        "content": '{"temperature":25,"condition":"averses légères"}',
    },
]

t_a = run_test(
    "TEST A — historique tool + tools",
    messages_a,
    use_tools=True,
)


# ---------------------------------------------------------
# TEST B
# même historique
# MAIS SANS tools
# ---------------------------------------------------------

t_b = run_test(
    "TEST B — historique tool SANS tools",
    messages_a,
    use_tools=False,
)


# ---------------------------------------------------------
# TEST C
# historique sans tool_call_id
# ---------------------------------------------------------

messages_c = base + [
    assistant_message,
    {
        "role": "tool",
        "content": '{"temperature":25,"condition":"averses légères"}',
    },
]

t_c = run_test(
    "TEST C — tool result sans tool_call_id",
    messages_c,
    use_tools=True,
)


# ---------------------------------------------------------
# TEST D
# remplacer le message tool par un message utilisateur
# ---------------------------------------------------------

messages_d = base + [
    assistant_message,
    {
        "role": "user",
        "content": (
            "Résultat de get_weather : "
            '{"temperature":25,"condition":"averses légères"}'
        ),
    },
]

t_d = run_test(
    "TEST D — résultat injecté comme user",
    messages_d,
    use_tools=True,
)


# ---------------------------------------------------------
# RÉSULTATS
# ---------------------------------------------------------

print("\n")
print("=" * 70)
print("RÉSULTATS")
print("=" * 70)

print(f"TEST A : {t_a:.3f}s")
print(f"TEST B : {t_b:.3f}s")
print(f"TEST C : {t_c:.3f}s")
print(f"TEST D : {t_d:.3f}s")

print("=" * 70)