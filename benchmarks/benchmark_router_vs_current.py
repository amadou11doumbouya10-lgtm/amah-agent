import os
import time
import json
from dotenv import load_dotenv
from groq import Groq
from config import TOOLS_DEFINITIONS

load_dotenv()

MODEL = os.getenv("MODEL", "openai/gpt-oss-120b")
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError("GROQ_API_KEY manquante")

client = Groq(api_key=API_KEY)

# ---------------------------------------------------------
# DEMANDE TEST
# ---------------------------------------------------------

USER_REQUEST = "Quelle est la météo actuelle à Conakry ?"

# ---------------------------------------------------------
# OUTILS MÉTÉO
# ---------------------------------------------------------

WEATHER_KEYWORDS = {
    "météo",
    "meteo",
    "temps",
    "température",
    "temperature",
    "pluie",
    "climat",
    "conakry",
}

def local_router(user_request):
    text = user_request.lower()

    if any(word in text for word in WEATHER_KEYWORDS):
        selected = [
            tool for tool in TOOLS_DEFINITIONS
            if tool.get("function", {}).get("name", "").startswith("get_weather")
        ]

        return selected, "weather"

    return TOOLS_DEFINITIONS, "all"


# ---------------------------------------------------------
# MESURE
# ---------------------------------------------------------

def run_test(label, tools):

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "Tu es Amah. Utilise les outils disponibles lorsque nécessaire."
            },
            {
                "role": "user",
                "content": USER_REQUEST
            }
        ],
        tools=tools,
        tool_choice="auto",
        max_tokens=256,
        temperature=0.2,
    )

    elapsed = time.perf_counter() - start

    choice = response.choices[0]
    usage = response.usage

    tool_calls = choice.message.tool_calls or []

    print(f"\n{'=' * 60}")
    print(label)
    print(f"{'=' * 60}")
    print(f"Outils envoyés : {len(tools)}")
    print(f"Temps          : {elapsed:.3f}s")
    print(f"Finish         : {choice.finish_reason}")
    print(f"Prompt tokens  : {usage.prompt_tokens}")
    print(f"Completion     : {usage.completion_tokens}")

    if tool_calls:
        print("Tool call(s) :")
        for call in tool_calls:
            print(
                f"  - {call.function.name}"
                f"({call.function.arguments})"
            )
    else:
        print("Tool call : aucun")

    return elapsed


# ---------------------------------------------------------
# ROUTAGE LOCAL
# ---------------------------------------------------------

router_tools, category = local_router(USER_REQUEST)

print("\n" + "=" * 60)
print("BENCHMARK AMAH ACTUEL VS TOOL ROUTER")
print("=" * 60)
print(f"Modèle : {MODEL}")
print(f"Demande : {USER_REQUEST}")
print(f"Catégorie détectée : {category}")
print(f"Nombre total d'outils : {len(TOOLS_DEFINITIONS)}")
print(f"Outils sélectionnés : {len(router_tools)}")
print("=" * 60)

# ---------------------------------------------------------
# TEST 1 — AMAH ACTUEL
# ---------------------------------------------------------

current_time = run_test(
    "TEST 1 — AMAH ACTUEL",
    TOOLS_DEFINITIONS
)

# ---------------------------------------------------------
# TEST 2 — TOOL ROUTER
# ---------------------------------------------------------

router_time = run_test(
    "TEST 2 — PREMIER TOOL ROUTER",
    router_tools
)

# ---------------------------------------------------------
# COMPARAISON
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("COMPARAISON")
print("=" * 60)

print(f"Amah actuel : {current_time:.3f}s")
print(f"Tool Router : {router_time:.3f}s")

if router_time < current_time:
    gain = current_time - router_time
    percent = (gain / current_time) * 100

    print(f"Gain       : {gain:.3f}s")
    print(f"Réduction  : {percent:.1f}%")
else:
    print("Le Tool Router n'est pas plus rapide sur ce test.")

print("=" * 60)