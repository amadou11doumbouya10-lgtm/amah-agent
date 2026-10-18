import time
from tools.planner import create_plan

print("=" * 60)
print("AMAH AGENT — BENCHMARK DEMANDE COMPLEXE")
print("=" * 60)

goal = (
    "Donne-moi la météo actuelle à Conakry, "
    "calcule 250000 multiplié par 37, "
    "puis donne-moi la date et l'heure actuelles."
)

print("\n[PERF] Demande complexe...")
start = time.perf_counter()

result = create_plan(goal)

elapsed = time.perf_counter() - start

print(f"\n[PERF] create_plan: {elapsed:.3f}s")
print("[PERF] résultat:")
print(result)

print("\n" + "=" * 60)
print("BENCHMARK TERMINÉ")
print("=" * 60)