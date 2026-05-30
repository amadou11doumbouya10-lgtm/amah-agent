import urllib.request
import urllib.parse
import re
import json
import time

# ── Cache LRU simple (TTL 10 minutes) ───────────────────────────────────────
_cache: dict = {}
_CACHE_TTL   = 600  # secondes


def _cache_get(key: str):
    if key in _cache:
        value, ts = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return value
        del _cache[key]
    return None


def _cache_set(key: str, value):
    # Limite le cache à 50 entrées
    if len(_cache) >= 50:
        oldest = min(_cache, key=lambda k: _cache[k][1])
        del _cache[oldest]
    _cache[key] = (value, time.time())


def web_search(query: str, num_results: int = 5) -> dict:
    cache_key = f"search:{query}:{num_results}"
    cached = _cache_get(cache_key)
    if cached:
        cached["cache"] = True
        return cached

    try:
        from ddgs import DDGS
    except ImportError:
        return {"error": "Module ddgs manquant. Lance : pip install ddgs"}

    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append({
                    "titre":   r.get("title", ""),
                    "url":     r.get("href", ""),
                    "resume":  r.get("body", ""),
                })

        result = {
            "success":   True,
            "query":     query,
            "resultats": results,
            "total":     len(results),
        }
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return {"error": str(e)}


def read_webpage(url: str) -> dict:
    cached = _cache_get(f"page:{url}")
    if cached:
        cached["cache"] = True
        return cached
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        }
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()

        # Détecter l'encodage
        charset = "utf-8"
        content_type = response.headers.get("Content-Type", "")
        if "charset=" in content_type:
            charset = content_type.split("charset=")[-1].strip()

        html = raw.decode(charset, errors="replace")

        # Supprimer scripts, styles, balises
        html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>",  " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<[^>]+>", " ", html)
        html = re.sub(r"&nbsp;", " ", html)
        html = re.sub(r"&amp;",  "&", html)
        html = re.sub(r"&lt;",   "<", html)
        html = re.sub(r"&gt;",   ">", html)
        html = re.sub(r"&quot;", '"', html)
        text = re.sub(r"\s+", " ", html).strip()

        if len(text) > 6000:
            text = text[:6000] + "\n\n[... contenu tronqué ...]"

        result = {"success": True, "url": url, "contenu": text}
        _cache_set(f"page:{url}", result)
        return result
    except urllib.error.URLError as e:
        return {"error": f"Impossible d'accéder à l'URL : {e}"}
    except Exception as e:
        return {"error": str(e)}
