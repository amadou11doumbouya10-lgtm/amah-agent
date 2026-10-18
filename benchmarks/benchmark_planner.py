import time
from tools.planner import create_plan, _run_step_once


def measure(name, func, *args, **kwargs):
    print(f"\n[PERF] {name}...")
    start = time.perf_counter()

    try:
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

        print(f"[PERF] {name}: {elapsed:.3f}s")
        print(f"[PERF] résultat: {str(result)[:500]}")

        return result, elapsed

    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"[PERF] {name}: ERREUR après {elapsed:.3f}s")
        print(f"[PERF] erreur: {e}")

        return None, elapsed


print("=" * 60)
print("AMAH AGENT — BENCHMARK PLANNER")
print("=" * 60)

# Test 1 : création d'un plan
goal = "Donne-moi la météo actuelle à Conakry et explique-moi brièvement la situation."

measure(
    "create_plan",
    create_plan,
    goal
)

print("\n" + "=" * 60)
print("BENCHMARK TERMINÉ")
print("=" * 60)