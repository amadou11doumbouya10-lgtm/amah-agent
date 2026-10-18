"""
Amah Agent - Benchmark Memory Recall V0.2.4

Objectifs :
- conserver les comportements validés de V0.2.3 ;
- vérifier la suppression d'une ancienne formulation devenue obsolète ;
- vérifier la conservation des informations réellement différentes ;
- vérifier création, fusion, cache et exact ;
- ne toucher ni à la vraie base SQLite ni à Groq.
"""

from __future__ import annotations

import json

import tools.memory_recall_v024 as mr


# ---------------------------------------------------------------------------
# État faux isolé
# ---------------------------------------------------------------------------

FAKE_MEMORIES = []
FAKE_SOURCES = []
SAVE_CALLS = 0
SEARCH_CALLS = 0
LLM_CALLS = 0


def fake_load_structured_memories():
    return [dict(item) for item in FAKE_MEMORIES]


def fake_find_sources(query, limit=6):
    global SEARCH_CALLS
    SEARCH_CALLS += 1
    return [dict(item) for item in FAKE_SOURCES[:limit]]


def fake_save_structured_memory(memory, previous_memory=None):
    global SAVE_CALLS

    SAVE_CALLS += 1

    new_memory = dict(memory)
    new_memory["_memory_id"] = (
        (FAKE_MEMORIES[-1].get("_memory_id", 0) + 1)
        if FAKE_MEMORIES
        else 1
    )

    if previous_memory:
        previous_id = previous_memory.get("_memory_id")
        FAKE_MEMORIES[:] = [
            item
            for item in FAKE_MEMORIES
            if item.get("_memory_id") != previous_id
        ]

    FAKE_MEMORIES.append(new_memory)

    return new_memory["_memory_id"]


def fake_summarize(prompt):
    global LLM_CALLS
    LLM_CALLS += 1

    if LLM_CALLS == 1:
        return json.dumps(
            {
                "version": 2,
                "topic": "Vision Amah",
                "type": "project",
                "summary": (
                    "Vision Amah est une entreprise informatique "
                    "orientée développement web."
                ),
                "decisions": [
                    "Créer une présence web professionnelle."
                ],
                "state": "Développement web.",
                "facts": [
                    "Projet technologique de Vision Amah."
                ],
                "keywords": [
                    "Vision Amah",
                    "web",
                ],
                "source_ids": [100, 101],
            },
            ensure_ascii=False,
        )

    if LLM_CALLS == 2:
        return json.dumps(
            {
                "version": 2,
                "topic": "Vision Amah",
                "type": "project",
                "summary": (
                    "Vision Amah travaille désormais sur le "
                    "développement web et l'IA."
                ),
                "decisions": [
                    "Créer une présence web professionnelle.",
                    "Ajouter des agents IA personnalisés.",
                ],
                "state": "Développement web et IA.",
                "facts": [
                    "Projet technologique de Vision Amah.",
                    "L'IA fait désormais partie du périmètre."
                ],
                "keywords": [
                    "Vision Amah",
                    "web",
                    "IA",
                ],
                "source_ids": [102, 103],
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "version": 2,
            "topic": "Vision Amah",
            "type": "project",
            "summary": (
                "Vision Amah travaille désormais sur le "
                "développement web, l'IA et des agents personnalisés."
            ),
            "decisions": [
                "Créer une présence web professionnelle.",
                "Ajouter des agents IA personnalisés.",
            ],
            "state": "Développement web, IA et agents personnalisés.",
            "facts": [
                "Projet technologique de Vision Amah.",
                "L'IA fait désormais partie du périmètre.",
            ],
            "keywords": [
                "Vision Amah",
                "web",
                "IA",
                "agents",
            ],
            "source_ids": [104],
        },
        ensure_ascii=False,
    )


# Isolation complète.
mr.load_structured_memories = fake_load_structured_memories
mr.find_sources = fake_find_sources
mr.save_structured_memory = fake_save_structured_memory


def reset_state():
    global FAKE_MEMORIES, FAKE_SOURCES, SAVE_CALLS, SEARCH_CALLS, LLM_CALLS

    FAKE_MEMORIES[:] = []
    FAKE_SOURCES[:] = []
    SAVE_CALLS = 0
    SEARCH_CALLS = 0
    LLM_CALLS = 0


def ok(condition, label):
    if condition:
        print(f"[OK]   {label}")
        return 1

    print(f"[FAIL] {label}")
    return 0


def separator():
    print("=" * 110)


def main():
    reset_state()

    passed = 0
    total = 0

    separator()
    print("BENCHMARK MEMORY RECALL V0.2.4")
    separator()
    print()

    # -----------------------------------------------------------------------
    # TEST 1 — mise à jour locale d'une ancienne formulation
    # -----------------------------------------------------------------------
    print("TEST 1 — MISE À JOUR D'UNE INFORMATION")
    print()

    old = (
        "Vision Amah est une entreprise informatique "
        "orientée développement web."
    )

    new = (
        "Vision Amah travaille désormais sur le "
        "développement web et l'IA."
    )

    final = mr.merge_summaries_with_topic(
        old,
        new,
        "Vision Amah",
    )

    print(final)
    print()

    checks = [
        old not in final,
        new in final,
        "Vision Amah" in final,
    ]

    for check, label in zip(
        checks,
        [
            "Ancienne formulation obsolète écartée",
            "Nouvelle information conservée",
            "Sujet conservé",
        ],
    ):
        total += 1
        passed += ok(check, label)

    print()

    # -----------------------------------------------------------------------
    # TEST 2 — deux informations différentes restent présentes
    # -----------------------------------------------------------------------
    print("TEST 2 — INFORMATIONS DIFFÉRENTES")
    print()

    old = (
        "Vision Amah propose des services informatiques "
        "aux entreprises."
    )
    new = (
        "Vision Amah prépare une présence web professionnelle."
    )

    final = mr.merge_summaries_with_topic(
        old,
        new,
        "Vision Amah",
    )

    print(final)
    print()

    checks = [
        old in final,
        new in final,
    ]

    for check, label in zip(
        checks,
        [
            "Ancienne information différente conservée",
            "Nouvelle information conservée",
        ],
    ):
        total += 1
        passed += ok(check, label)

    print()

    # -----------------------------------------------------------------------
    # TEST 3 — création
    # -----------------------------------------------------------------------
    print("TEST 3 — CRÉATION DE MÉMOIRE")
    print()

    FAKE_SOURCES[:] = [
        {
            "id": 100,
            "role": "user",
            "created_at": "2026-09-01",
            "content": "Vision Amah est une entreprise informatique orientée développement web.",
        },
        {
            "id": 101,
            "role": "assistant",
            "created_at": "2026-09-01",
            "content": "Le projet comprend une présence web professionnelle.",
        },
    ]

    result = mr.recall(
        query="Qu'est-ce qu'on avait dit sur Vision Amah ?",
        summarize_fn=fake_summarize,
        limit=6,
    )

    print(f"MODE      : {result.get('mode')}")
    print(f"TOPIC     : {result.get('topic')}")
    print(f"MEMORIES  : {len(FAKE_MEMORIES)}")
    print()

    checks = [
        result.get("mode") == "summary",
        result.get("topic") == "Vision Amah",
        len(FAKE_MEMORIES) == 1,
    ]

    for check, label in zip(
        checks,
        [
            "Première création = summary",
            "Sujet correct",
            "Une seule mémoire",
        ],
    ):
        total += 1
        passed += ok(check, label)

    print()

    # -----------------------------------------------------------------------
    # TEST 4 — fusion avec mise à jour
    # -----------------------------------------------------------------------
    print("TEST 4 — FUSION AVEC INFORMATION PLUS RÉCENTE")
    print()

    FAKE_SOURCES[:] = [
        {
            "id": 102,
            "role": "user",
            "created_at": "2026-09-15",
            "content": "Vision Amah travaille désormais sur le développement web et l'IA.",
        },
        {
            "id": 103,
            "role": "assistant",
            "created_at": "2026-09-15",
            "content": "Le périmètre inclut maintenant l'IA.",
        },
    ]

    result = mr.recall(
        query="Qu'est-ce qu'on avait décidé sur Vision Amah ?",
        summarize_fn=fake_summarize,
        limit=6,
    )

    summary = result.get("summary", "")
    state = result.get("state", "")

    print(f"MODE      : {result.get('mode')}")
    print(f"SUMMARY   : {summary}")
    print(f"STATE     : {state}")
    print(f"SOURCES   : {result.get('source_ids')}")
    print()

    checks = [
        result.get("mode") == "summary_updated",
        "web." not in summary.lower() or "désormais" not in summary.lower(),
        "IA" in summary,
        "développement web et l'IA" in summary,
        state == "Développement web et IA.",
        len(FAKE_MEMORIES) == 1,
    ]

    labels = [
        "Mode = summary_updated",
        "Pas de doublon de l'ancienne formulation",
        "Nouvelle information IA conservée",
        "Nouvelle formulation conservée",
        "État actuel mis à jour",
        "Toujours une seule mémoire",
    ]

    for check, label in zip(checks, labels):
        total += 1
        passed += ok(check, label)

    print()

    # -----------------------------------------------------------------------
    # TEST 5 — conservation structurée
    # -----------------------------------------------------------------------
    print("TEST 5 — CONSERVATION DES INFORMATIONS STRUCTURÉES")
    print()

    mem = FAKE_MEMORIES[0]

    print(f"Décisions : {mem.get('decisions')}")
    print(f"Faits     : {mem.get('facts')}")
    print(f"Sources   : {mem.get('source_ids')}")
    print()

    checks = [
        "Créer une présence web professionnelle." in mem.get("decisions", []),
        "Ajouter des agents IA personnalisés." in mem.get("decisions", []),
        100 in mem.get("source_ids", []),
        101 in mem.get("source_ids", []),
        102 in mem.get("source_ids", []),
        103 in mem.get("source_ids", []),
    ]

    labels = [
        "Ancienne décision conservée",
        "Nouvelle décision conservée",
        "Source 100 conservée",
        "Source 101 conservée",
        "Source 102 conservée",
        "Source 103 conservée",
    ]

    for check, label in zip(checks, labels):
        total += 1
        passed += ok(check, label)

    print()

    # -----------------------------------------------------------------------
    # TEST 6 — cache
    # -----------------------------------------------------------------------
    print("TEST 6 — CACHE SANS NOUVELLE SOURCE")
    print()

    llm_before = LLM_CALLS
    search_before = SEARCH_CALLS

    FAKE_SOURCES[:] = [
        {
            "id": 102,
            "role": "user",
            "created_at": "2026-09-15",
            "content": "Vision Amah travaille désormais sur le développement web et l'IA.",
        },
        {
            "id": 103,
            "role": "assistant",
            "created_at": "2026-09-15",
            "content": "Le périmètre inclut maintenant l'IA.",
        },
    ]

    result = mr.recall(
        query="Qu'est-ce qu'on avait décidé sur Vision Amah ?",
        summarize_fn=fake_summarize,
        limit=6,
    )

    print(f"MODE          : {result.get('mode')}")
    print(f"CACHE         : {result.get('cached')}")
    print(f"LLM AVANT     : {llm_before}")
    print(f"LLM APRÈS     : {LLM_CALLS}")
    print(f"RECHERCHES    : {SEARCH_CALLS - search_before}")
    print()

    checks = [
        result.get("mode") == "summary_cached",
        result.get("cached") is True,
        LLM_CALLS == llm_before,
        SEARCH_CALLS - search_before == 1,
    ]

    labels = [
        "Mode = summary_cached",
        "Cache = True",
        "Aucun nouvel appel LLM",
        "Une seule recherche historique",
    ]

    for check, label in zip(checks, labels):
        total += 1
        passed += ok(check, label)

    print()

    # -----------------------------------------------------------------------
    # TEST 7 — exact
    # -----------------------------------------------------------------------
    print("TEST 7 — DEMANDE EXACTE")
    print()

    FAKE_SOURCES[:] = [
        {
            "id": 102,
            "role": "user",
            "created_at": "2026-09-15",
            "content": "Vision Amah travaille désormais sur le développement web et l'IA.",
        },
        {
            "id": 103,
            "role": "assistant",
            "created_at": "2026-09-15",
            "content": "Le périmètre inclut maintenant l'IA.",
        },
    ]

    result = mr.recall(
        query="Montre-moi exactement les messages sur Vision Amah.",
        summarize_fn=fake_summarize,
        limit=6,
    )

    print(f"MODE      : {result.get('mode')}")
    print(f"SOURCES   : {len(result.get('sources', []))}")
    print()

    checks = [
        result.get("mode") == "exact",
        len(result.get("sources", [])) == 2,
    ]

    for check, label in zip(
        checks,
        [
            "Mode exact",
            "Sources originales retrouvées",
        ],
    ):
        total += 1
        passed += ok(check, label)

    print()

    # -----------------------------------------------------------------------
    # TEST 8 — nouvelle source après cache
    # -----------------------------------------------------------------------
    print("TEST 8 — NOUVELLE SOURCE APRÈS LE CACHE")
    print()

    FAKE_SOURCES[:] = [
        {
            "id": 104,
            "role": "user",
            "created_at": "2026-09-20",
            "content": "Vision Amah ajoute des agents personnalisés.",
        }
    ]

    result = mr.recall(
        query="Qu'est-ce qu'on sait maintenant sur Vision Amah ?",
        summarize_fn=fake_summarize,
        limit=6,
    )

    print(f"MODE      : {result.get('mode')}")
    print(f"SOURCES   : {result.get('source_ids')}")
    print(f"MEMORIES  : {len(FAKE_MEMORIES)}")
    print()

    checks = [
        result.get("mode") == "summary_updated",
        104 in result.get("source_ids", []),
        len(FAKE_MEMORIES) == 1,
        "agents" in result.get("summary", "").lower(),
    ]

    labels = [
        "Nouvelle source déclenche une mise à jour",
        "Nouvelle source conservée",
        "Toujours une seule mémoire",
        "Nouvelle information présente",
    ]

    for check, label in zip(checks, labels):
        total += 1
        passed += ok(check, label)

    print()

    # -----------------------------------------------------------------------
    # Résultat
    # -----------------------------------------------------------------------
    separator()
    print("RÉSULTAT")
    separator()
    print()
    print(f"Tests réussis : {passed}/{total}")
    print(f"Mémoires      : {len(FAKE_MEMORIES)}")
    print(f"Appels faux LLM : {LLM_CALLS}")
    print(f"Recherches     : {SEARCH_CALLS}")
    print()

    if passed == total:
        print("✅ MEMORY RECALL V0.2.4 VALIDÉ")
    else:
        print("❌ MEMORY RECALL V0.2.4 À CORRIGER")


if __name__ == "__main__":
    main()
