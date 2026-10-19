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


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
    # Pas de "br" : brotli n'est pas dans la bibliothèque standard
    "Accept-Encoding": "gzip, deflate",
}


def fetch_page_html(url: str) -> str:
    """HTML décodé de l'URL. Décompresse gzip/deflate : certains sites
    (python.org) compressent même sans qu'on le demande, et read_webpage
    renvoyait alors des octets illisibles."""
    import gzip
    import zlib
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=12) as response:
        raw = response.read()
        encoding = (response.headers.get("Content-Encoding") or "").lower()
        content_type = response.headers.get("Content-Type", "")
    if "gzip" in encoding or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    elif "deflate" in encoding:
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    charset = "utf-8"
    if "charset=" in content_type:
        charset = content_type.split("charset=")[-1].split(";")[0].strip() or "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


# Hébergeurs dont les sites n'ont qu'UN niveau de sous-domaine (nom-du-site.vercel.app)
_PLATFORM_SUFFIXES = ("vercel.app", "netlify.app", "github.io", "pages.dev", "web.app",
                      "firebaseapp.com", "onrender.com", "herokuapp.com", "surge.sh",
                      "glitch.me", "replit.app", "railway.app", "fly.dev")


def url_variants(url: str) -> list:
    """Autres écritures probables d'une adresse dictée à voix haute.

    La reconnaissance vocale écrit souvent un tiret comme un point :
    "campusmarket-nu.vercel.app" devient "campusmarket.nu.vercel.app", une
    adresse qui n'existe pas (test réel du 18/10/2026). Sur ces hébergeurs, un
    point de trop dans le nom du site est forcément une erreur."""
    raw = str(url or "").strip()
    parsed = urllib.parse.urlparse(raw if re.match(r"https?://", raw, re.I) else "https://" + raw)
    host = (parsed.hostname or "").lower()
    variants = []
    for suffix in _PLATFORM_SUFFIXES:
        if host.endswith("." + suffix):
            name = host[: -len(suffix) - 1]
            if "." in name:
                netloc = name.replace(".", "-") + "." + suffix
                if parsed.port:
                    netloc += f":{parsed.port}"
                variants.append(parsed._replace(netloc=netloc).geturl())
    return variants


def fetch_main_text(url: str) -> dict:
    """{"url", "titre", "texte"} : contenu principal complet (sans troncature).
    Si l'adresse ne répond pas, essaie ses variantes probables (url_variants) ;
    "adresse_corrigee" indique alors l'adresse qui a marché."""
    cached = _cache_get(f"main:{url}")
    if cached:
        return cached
    from tools.page_text import extract_main_text
    try:
        result = {"url": url, **extract_main_text(fetch_page_html(url))}
    except Exception as first_error:
        for variant in url_variants(url):
            try:
                result = {"url": variant, "adresse_corrigee": variant,
                          **extract_main_text(fetch_page_html(variant))}
                break
            except Exception:
                continue
        else:
            raise first_error
    _cache_set(f"main:{url}", result)
    return result


def read_webpage(url: str) -> dict:
    """Contenu principal de la page (article), sans menus ni bandeaux."""
    try:
        page = fetch_main_text(url)
        text = page["texte"]
        if not text:
            return {"error": "Page vide ou générée par JavaScript : ouvre-la avec "
                             "open_browser puis utilise get_page_text."}
        total = len(text)
        if total > 6000:
            text = text[:6000] + "\n\n[... contenu tronqué ...]"
        result = {"success": True, "url": page.get("url", url), "titre": page["titre"],
                  "contenu": text, "longueur_totale": total}
        if page.get("adresse_corrigee"):
            result["note"] = (f"L'adresse {url} ne répondait pas ; c'est "
                              f"{page['adresse_corrigee']} qui a marché (erreur de dictée probable).")
        return result
    except urllib.error.URLError as e:
        return {"error": f"Impossible d'accéder à l'URL : {e}"}
    except Exception as e:
        return {"error": str(e)}
