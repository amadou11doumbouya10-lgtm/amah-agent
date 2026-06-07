import webbrowser
import urllib.parse


def open_youtube(query: str) -> dict:
    """Ouvre YouTube avec une recherche dans le navigateur par défaut."""
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    try:
        webbrowser.open(url)
        return {"success": True, "url": url, "recherche": query}
    except Exception as e:
        return {"error": str(e)}


def play_music(query: str) -> dict:
    """Lance une recherche musicale sur YouTube Music dans le navigateur."""
    import urllib.parse
    url = f"https://music.youtube.com/search?q={urllib.parse.quote(query)}"
    try:
        webbrowser.open(url)
        return {"success": True, "musique": query, "url": url,
                "message": f"Lecture de '{query}' sur YouTube Music."}
    except Exception as e:
        return {"error": str(e)}


def search_youtube(query: str, num_results: int = 5) -> dict:
    """Cherche des vidéos YouTube via DuckDuckGo et retourne les résultats sans ouvrir le navigateur."""
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(f"site:youtube.com {query}", max_results=num_results):
                results.append({
                    "titre": r.get("title", ""),
                    "url":   r.get("href", ""),
                    "desc":  r.get("body", "")[:150],
                })
        return {"success": True, "recherche": query, "resultats": results, "total": len(results)}
    except ImportError:
        return {"error": "Module ddgs manquant. Lance : pip install ddgs"}
    except Exception as e:
        return {"error": str(e)}
