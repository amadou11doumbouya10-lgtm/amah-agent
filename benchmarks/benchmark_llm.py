import time
from groq_client import GroqClient

client = GroqClient.get()

print("=" * 60)
print("AMAH AGENT — BENCHMARK LLM DIRECT")
print("=" * 60)

messages = [
    {
        "role": "system",
        "content": "Réponds uniquement avec un JSON valide. Aucun outil, aucun appel de fonction."
    },
    {
        "role": "user",
        "content": "Réponds avec exactement : {\"test\": \"ok\"}"
    }
]

print("\n[PERF] Appel LLM direct...")

start = time.perf_counter()

try:
    response = client.chat(
        messages=messages,
        model="openai/gpt-oss-120b",
        response_format={"type": "json_object"},
        max_tokens=100,
        temperature=0.2,
    )

    elapsed = time.perf_counter() - start

    print(f"[PERF] LLM direct: {elapsed:.3f}s")
    print("[PERF] Réponse:")
    print(response.choices[0].message.content)

except Exception as e:
    elapsed = time.perf_counter() - start
    print(f"[PERF] ERREUR après {elapsed:.3f}s")
    print(e)

print("\n" + "=" * 60)
print("BENCHMARK TERMINÉ")
print("=" * 60)