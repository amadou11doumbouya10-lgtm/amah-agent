# Benchmarks d'Amah

Scripts de mesure et de vérification. À lancer **depuis la racine du projet** :

```bash
py -3.13 -m benchmarks.benchmark_tool_router
```

## À lancer après chaque modification

Ces deux vérifications n'appellent pas l'IA et renvoient un code de sortie 1 en
cas d'échec :

| Script | Vérifie |
|---|---|
| `benchmark_tool_router.py` | Le routeur partagé sur 95 phrases (40 de l'audit, 55 formulées autrement que ses mots-clés). Attendu : 100 %. |
| `benchmark_guard.py` | Le garde-fou des actions sensibles : refus par défaut, Oui/Non, filtre de commandes, terminal. Attendu : 15/15. |

Pour le routeur, n'ajoute pas un mot-clé juste pour faire passer une phrase du
jeu « nouvelles phrases » : ce jeu mesure la compréhension de formulations
inédites. Les anciens benchmarks du routeur reprenaient les phrases de ses
motifs et donnaient 100 % alors que le routeur ratait 80 % des vraies demandes.

## Benchmarks hors ligne

`benchmark_complex.py`, `benchmark_complex_full.py`, `benchmark_context_agent.py`,
`benchmark_context_profiles.py`, `benchmark_conversation_search_v022.py`,
`benchmark_planner.py`, `benchmark_router_load.py`, `benchmark_router_v03.py`,
`benchmark_tool.py`

## Benchmarks qui appellent Groq

Ils consomment le quota journalier (200 000 tokens par jour et par clé sur
gpt-oss-120b, soit environ 40 demandes avec outils). Espace-les.

`benchmark_99tools_isolation.py`, `benchmark_agent.py`, `benchmark_content_isolation.py`,
`benchmark_context.py`, `benchmark_generation_debug.py`, `benchmark_generation_threshold.py`,
`benchmark_llm.py`, `benchmark_llm_context_clean.py`, `benchmark_memory_recall_v024.py`,
`benchmark_model_variability.py`, `benchmark_multiturn_clean.py`, `benchmark_no_tools_second.py`,
`benchmark_post_tool_minimal.py`, `benchmark_router_vs_current.py`, `benchmark_tool_choice.py`,
`benchmark_tool_count.py`, `benchmark_tool_loop*.py`

Certains écrivent dans `amah_memory.db` (historique, résumés mis en cache) :
vérifie les tables `memories` et `tool_usage` après un essai.

Les benchmarks des versions abandonnées (router_v01/v02, context_manager,
memory_recall v01 à v023…) sont dans `archives/benchmarks/`, hors du dépôt.
