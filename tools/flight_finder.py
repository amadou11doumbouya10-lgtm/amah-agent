import webbrowser
import urllib.parse


def search_flights(from_city: str, to_city: str, date: str = None) -> dict:
    """Recherche des vols entre deux villes, affiche des résultats et ouvre Google Flights."""
    try:
        from ddgs import DDGS

        query = f"vols {from_city} {to_city} billet avion"
        if date:
            query += f" {date}"

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query + " pas cher comparer", max_results=6):
                results.append({
                    "titre": r.get("title", ""),
                    "url":   r.get("href", ""),
                    "desc":  r.get("body", "")[:180],
                })

        # Ouvre Google Flights dans le navigateur
        gf_q   = urllib.parse.quote(f"{from_city} to {to_city} flights {date or ''}")
        gf_url = f"https://www.google.com/travel/flights?q={gf_q}"
        webbrowser.open(gf_url)

        return {
            "success":        True,
            "trajet":         f"{from_city} → {to_city}",
            "date":           date or "flexible",
            "resultats":      results,
            "google_flights": gf_url,
            "conseil":        "Google Flights vient de s'ouvrir. Comparez aussi sur Skyscanner et Kayak.",
        }
    except ImportError:
        return {"error": "Module ddgs manquant. Lance : pip install ddgs"}
    except Exception as e:
        return {"error": str(e)}
