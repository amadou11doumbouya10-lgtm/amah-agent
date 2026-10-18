import time
from tools.planner import create_plan, _run_step_once

print("=" * 60)
print("AMAH AGENT — BENCHMARK COMPLEXE COMPLET")
print("=" * 60)

goal = (
    "Donne-moi la météo actuelle à Conakry, "
    "calcule 250000 multiplié par 37, "
    "puis donne-moi la date et l'heure actuelles."
)

# --------------------------------------------------
# 1. Création du plan
# --------------------------------------------------

print("\n[1] Création du plan...")
start_total = time.perf_counter()
start = time.perf_counter()

plan = create_plan(goal)

plan_time = time.perf_counter() - start

print(f"[PERF] create_plan: {plan_time:.3f}s")

if not plan.get("success"):
    print("[ERREUR]", plan)
    raise SystemExit(1)

print("\nPlan généré :")

for step in plan["etapes"]:
    print(
        f"  {step['n']}. "
        f"{step['outil']} "
        f"{step.get('params', {})}"
    )

# --------------------------------------------------
# 2. Exécution des outils
# --------------------------------------------------

total_tool_time = 0

print("\n[2] Exécution des outils...")

for step in plan["etapes"]:

    tool_name = step["outil"]
    params = step.get("params", {})

    print(f"\n→ {tool_name}")

    start = time.perf_counter()

    result = _run_step_once(
        tool_name,
        params
    )

    elapsed = time.perf_counter() - start
    total_tool_time += elapsed

    print(f"[PERF] {tool_name}: {elapsed:.3f}s")
    print(f"[RESULT] {str(result)[:500]}")

# --------------------------------------------------
# 3. Résultat global
# --------------------------------------------------

total_time = time.perf_counter() - start_total

print("\n" + "=" * 60)
print("RÉSULTATS")
print("=" * 60)

print(f"\nTemps création plan : {plan_time:.3f}s")
print(f"Temps outils        : {total_tool_time:.3f}s")
print(f"Temps TOTAL         : {total_time:.3f}s")

if total_time > 30:
    print("\n⚠️ LATENCE > 30 SECONDES")

elif total_time > 15:
    print("\n⚠️ LATENCE ÉLEVÉE")

else:
    print("\n✅ LATENCE ACCEPTABLE")

print("\n" + "=" * 60)
print("BENCHMARK TERMINÉ")
print("=" * 60)