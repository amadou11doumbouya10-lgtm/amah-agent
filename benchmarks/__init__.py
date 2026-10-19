"""Benchmarks d'Amah (à lancer avec py -3.13 -m benchmarks.<nom>).

Les tests n'écrivent jamais dans le journal de session de l'utilisateur
(amah_journal.txt), même si son .env contient AMAH_JOURNAL=1 : load_dotenv ne
remplace pas une variable déjà définie. Avant, benchmark_guard y écrivait ses
suppressions simulées.
"""
import os

os.environ["AMAH_JOURNAL"] = "0"
