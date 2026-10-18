import os
import json
import time

from groq import Groq
from dotenv import load_dotenv

from config import SYSTEM_PROMPT, MODEL, TOOLS_DEFINITIONS
from tools import TOOL_FUNCTIONS

load_dotenv()

print("=" * 60)
print("AMAH — TEST LLM AVEC/SANS OUTILS")
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

# --------------------------------------------------
# TEST 1 : avec outils
# --------------------------------------------------

print("\n[TEST 1]")
print("Appel initial AVEC TOOLS_DEFINITIONS")

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

print(f"Temps : {elapsed:.3f}s")

msg = response.choices[0].message

print("Finish reason :", response.choices[0].finish_reason)

if not msg.tool_calls:
    print("Aucun tool call.")
    raise SystemExit(0)

tc = msg.tool_calls[0]

print("Outil :", tc.function.name)
print("Args  :", tc.function.arguments)

# --------------------------------------------------
# Ajouter appel assistant
# --------------------------------------------------

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
    ]
})

# --------------------------------------------------
# Simuler le résultat de l'outil
# --------------------------------------------------

messages.append({
    "role": "tool",
    "tool_call_id": tc.id,
    "content": json.dumps({
        "success": True,
        "ville": "Conakry",
        "temperature": "25°C",
        "condition": "Light rain shower"
    })
})

# --------------------------------------------------
# TEST 2 : sans outils + consigne texte
# --------------------------------------------------

print("\n[TEST 2]")
print("Même contexte SANS TOOLS_DEFINITIONS")
print("Réponse texte uniquement")

messages.append({
    "role": "user",
    "content": (
        "À partir des informations disponibles, "
        "réponds uniquement en texte. "
        "N'utilise aucun outil."
    )
})

start = time.perf_counter()

response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    max_tokens=512,
    temperature=0.4,
)

elapsed = time.perf_counter() - start

print(f"Temps : {elapsed:.3f}s")
print("Finish reason :", response.choices[0].finish_reason)

print("\nRéponse :")
print(response.choices[0].message.content)

print("\n" + "=" * 60)
print("FIN DU TEST")
print("=" * 60)