import os
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = os.getenv("MODEL", "openai/gpt-oss-120b")
API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=API_KEY)

tool_call = {
    "id": "call_test",
    "type": "function",
    "function": {
        "name": "get_weather_simple",
        "arguments": '{"location":"Conakry"}'
    }
}

tool_result = {
    "role": "tool",
    "tool_call_id": "call_test",
    "content": '{"location":"Conakry","temperature":25,"condition":"light rain shower"}'
}

messages = [
    {
        "role": "system",
        "content": "Tu es Amah, un assistant local. Réponds clairement et brièvement."
    },
    {
        "role": "user",
        "content": "Quelle est la météo actuelle à Conakry ?"
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [tool_call]
    },
    tool_result
]

print("=" * 70)
print("BENCHMARK — POST TOOL MINIMAL")
print("=" * 70)
print(f"MODEL: {MODEL}")
print("=" * 70)

for i in range(1, 7):
    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=[],
        tool_choice="none",
        max_tokens=256,
        temperature=0.2,
    )

    elapsed = time.perf_counter() - start

    choice = response.choices[0]
    usage = response.usage

    print(f"\nTEST {i}/6")
    print(f"Temps             : {elapsed:.3f}s")
    print(f"Finish reason     : {choice.finish_reason}")
    print(f"Prompt tokens     : {usage.prompt_tokens}")
    print(f"Completion tokens : {usage.completion_tokens}")
    print(f"Réponse           : {choice.message.content!r}")