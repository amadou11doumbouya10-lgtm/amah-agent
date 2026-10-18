"""
Amah Agent - Benchmark Conversation Search V0.2.2

Benchmark de la recherche conversationnelle V0.2.2.
"""

from __future__ import annotations

import time

from tools.conversation_search_v022 import (
    expand_terms,
    extract_terms,
    search_conversations,
)


TEST_QUERIES = [
    "Qu'est-ce qu'on avait décidé sur le Router ?",
    "Qu'est-ce qu'on avait dit sur Amah ?",
    "Qu'est-ce qu'on avait dit sur le projet Amah Agent ?",
    "Parle-moi de Vision Amah",
    "Qu'avait-on décidé pour le projet ?",
    "Que sais-tu sur Amah Agent ?",
    "Qu'est-ce qu'on avait décidé sur le routeur ?",
    "Qu'est-ce qu'on avait dit sur les performances d'Amah ?",

    # Tests de généralisation
    "Qu'est-ce qu'on avait dit sur Shopify ?",
    "Qu'est-ce qu'on avait dit sur Vertex Shop ?",
    "Qu'est-ce qu'on avait dit sur Python ?",
    "Qu'est-ce qu'on avait dit sur GitHub ?",
]


def print_separator():
    print("=" * 110)


def main():
    print_separator()
    print("BENCHMARK CONVERSATION SEARCH V0.2.2")
    print_separator()
    print()

    total_time = 0.0
    total_results = 0

    for query in TEST_QUERIES:

        print_separator()
        print(f"REQUETE : {query}")

        terms = extract_terms(query)
        groups = expand_terms(terms)

        print(f"TERMES  : {terms}")
        print(f"GROUPES : {groups}")
        print()

        start = time.perf_counter()

        results = search_conversations(
            query=query,
            limit=8,
        )

        elapsed = time.perf_counter() - start

        total_time += elapsed
        total_results += len(results)

        print(f"RESULTATS : {len(results)}")
        print(f"TEMPS     : {elapsed * 1000:.2f} ms")
        print()

        for result in results:

            preview = result["content"]

            if len(preview) > 350:
                preview = preview[:350] + "..."

            print(
                f"#{result['id']} "
                f"score={result.get('score', 0):.2f} "
                f"match={result.get('matched_terms', 0)} "
                f"groups={result.get('matched_groups', [])} "
                f"[{result['role']}] "
                f"{preview}"
            )

        print()

    print_separator()
    print("RESUME")
    print_separator()

    print(f"Requetes testees : {len(TEST_QUERIES)}")
    print(f"Resultats totaux : {total_results}")

    if TEST_QUERIES:
        print(
            f"Temps moyen     : "
            f"{(total_time / len(TEST_QUERIES)) * 1000:.2f} ms"
        )

    print()


if __name__ == "__main__":
    main()