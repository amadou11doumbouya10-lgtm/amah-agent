import os
import json
import time

from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS
from tools import TOOL_FUNCTIONS

load_dotenv()

print("=" * 60)
print("AMAH — BENCHMARK CONTEXTE LLM")
print("=" * 60)

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise SystemExit("GROQ_API_KEY introuvable")

client = Groq(api_key=api_key)

messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    },
    {
        "role": "user",
        "content": (
            "Donne-moi la météo actuelle à Conakry, "
            "calcule 250000 multiplié par 37, "
            "puis donne-moi la date et l'heure actuelles."
        )
    }
]

def context_stats(messages):
    serialized = json.dumps(
        messages,
        ensure_ascii=False,
        default=str
    )

    return {
        "messages": len(messages),
        "chars": len(serialized),
        "approx_tokens": len(serialized) // 4
    }

def call_llm(label):
    stats = context_stats(messages)

    print("\n" + "-" * 60)
    print(label)
    print(f"Messages       : {stats['messages']}")
    print(f"Caractères     : {stats['chars']}")
    print(f"Tokens approx. : {stats['approx_tokens']}")
    print("Appel LLM...")

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

    print(f"Temps LLM      : {elapsed:.3f}s")

    return response


# --------------------------------------------------
# LLM #1
# --------------------------------------------------

response = call_llm("LLM #1")

msg = response.choices[0].message

print("Finish reason :", response.choices[0].finish_reason)

if not msg.tool_calls:
    print("Réponse finale :", msg.content)
    raise SystemExit(0)

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
# Outil #1
# --------------------------------------------------

tc = msg.tool_calls[0]

name = tc.function.name
args = json.loads(tc.function.arguments or "{}")

print("\nOutil #1 :", name)
print("Arguments :", args)

func = TOOL_FUNCTIONS.get(name)

start = time.perf_counter()

result = func(**args)

tool_time = time.perf_counter() - start

print(f"Temps outil : {tool_time:.3f}s")

messages.append({
    "role": "tool",
    "tool_call_id": tc.id,
    "content": json.dumps(
        result,
        ensure_ascii=False,
        default=str
    )
})

# --------------------------------------------------
# LLM #2
# --------------------------------------------------

response = call_llm("LLM #2")

print(
    "\nFinish reason :",
    response.choices[0].finish_reason
)

print(
    "Tool calls :",
    len(response.choices[0].message.tool_calls or [])
)

print("\n" + "=" * 60)
print("FIN DU BENCHMARK")
print("=" * 60)