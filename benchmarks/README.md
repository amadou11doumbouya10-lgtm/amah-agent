# Benchmarks d'Amah

Scripts de mesure et de vérification. À lancer **depuis la racine du projet** :

```bash
py -3.13 -m benchmarks.benchmark_tool_router
```

## À lancer après chaque modification

Ces vérifications n'appellent pas l'IA et renvoient un code de sortie 1 en
cas d'échec :

| Script | Vérifie |
|---|---|
| `benchmark_tool_router.py` | Le routeur partagé sur 101 phrases (40 de l'audit, 55 formulées autrement que ses mots-clés, 6 régressions vues en vrai). Attendu : 100 %. |
| `benchmark_guard.py` | Le garde-fou des actions sensibles : refus par défaut, Oui/Non, filtre de commandes, terminal. Attendu : 15/15. |
| `benchmark_license.py` | Les licences signées : clé valide acceptée, autre machine / clé modifiée / ancien format refusés, clé privée du .env = clé publique du code. Attendu : 11/11. |
| `benchmark_history.py` | Conservation de l'historique (AMAH_HISTORY_DAYS) et reprise de la dernière session. Attendu : 11/11. |
| `benchmark_page_text.py` | Contenu principal des pages (sans menus ni bandeaux), découpage et arrêt de la lecture à voix haute. Attendu : 14/14. |
| `benchmark_injection.py` | Aucun texte externe dans le code PowerShell (notification, repli vocal, presse-papiers). Attendu : 13/13. |
| `benchmark_initiatives.py` | Emails importants, alertes (nouveaux emails seulement), briefing du jour. Attendu : 18/18. |
| `benchmark_conversation.py` | Briques communes aux 3 interfaces (troncature, coupure de l'historique, texte pour la voix), confirmations du terminal, et compréhension des transcriptions vocales réelles (mot de réveil, fermeture, calcul dicté). Attendu : 21/21. |
| `benchmark_interfaces.py --sans-ia` | Les demandes qui ne doivent jamais appeler l'IA (heure, briefing, lecture, arrêt) dans les 3 interfaces. Attendu : 12/12. |

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

**`benchmark_voice.py`** (réseau, **aucun appel Groq**) : 18 phrases dites par
4 voix de synthèse (Henri, Denise, Hortense, Henri + bruit) passent par la
reconnaissance Google des interfaces, puis on vérifie ce qu'Amah comprend.
~3 minutes, ffmpeg requis pour les voix edge-tts. Mesuré le 18/10/2026 :
réveil 7/8, interface vocale 64/64, bouton micro + terminal 60/60. Ne teste
ni le micro réel, ni ta voix, ni le mode Live Gemini.

**`benchmark_interfaces.py`** (sans option) est le test de référence de
l'étape 1 du plan Amah Core : les mêmes 10 demandes envoyées à la fenêtre, à la
voix et au terminal (~25 appels, ~150 000 tokens, ~15 minutes avec les pauses).
Mesuré le 18/10/2026 : fenêtre 10/10, voix 10/10, terminal 9/10. Objectif de
l'étape 1 : 30/30.

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
