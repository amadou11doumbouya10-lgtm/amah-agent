import time
from tools.planner import _run_step_once

print("=" * 60)
print("AMAH AGENT — BENCHMARK OUTIL")
print("=" * 60)

start = time.perf_counter()

result = _run_step_once(
    "get_weather",
    {"location": "Conakry"}
)

elapsed = time.perf_counter() - start

print(f"\n[PERF] get_weather: {elapsed:.3f}s")
print("[PERF] résultat:")
print(result)

print("\n" + "=" * 60)
print("BENCHMARK TERMINÉ")
print("=" * 60)