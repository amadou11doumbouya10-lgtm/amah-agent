"""YouTube et musique.

La musique se joue dans le navigateur par défaut (elle continue quand Amah se
ferme) et se pilote par les touches multimédia de Windows, qui marchent avec
tout lecteur : YouTube dans le navigateur, Spotify, VLC…
"""
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
import webbrowser

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
# Chaque vidéo de la page de résultats : identifiant puis titre (ytInitialData)
_VIDEO = re.compile(r'"videoRenderer":\{"videoId":"([\w-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"\}',
                    re.DOTALL)
# Mots d'une demande qui ne désignent pas l'œuvre ("lance la musique de Santo")
_NOT_TITLE = {"musique", "musiques", "music", "chanson", "chansons", "video", "videos", "clip",
              "clips", "youtube", "morceau", "titre", "album", "audio", "officiel", "official",
              "les", "des", "une", "sur", "par", "avec", "pour", "lance", "joue", "mets"}


def open_youtube(query: str) -> dict:
    """Ouvre YouTube avec une recherche dans le navigateur par défaut."""
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    try:
        webbrowser.open(url)
        return {"success": True, "url": url, "recherche": query}
    except Exception as e:
        return {"error": str(e)}


def _compact(text) -> str:
    text = unicodedata.normalize("NFD", str(text or "").lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in text if not unicodedata.combining(c)))


def search_videos(query: str, limit: int = 10) -> list:
    """[(identifiant, titre)] des premières vidéos de la recherche YouTube."""
    url = ("https://www.youtube.com/results?search_query="
           + urllib.parse.quote(query) + "&hl=fr")
    request = urllib.request.Request(url, headers={
        "User-Agent": _UA, "Accept-Language": "fr-FR,fr;q=0.9",
        "Cookie": "CONSENT=YES+1; SOCS=CAI",       # pas de page de consentement
    })
    html = urllib.request.urlopen(request, timeout=10).read().decode("utf-8", "replace")
    videos = []
    for match in _VIDEO.finditer(html):
        title = match.group(2)
        try:
            title = json.loads(f'"{title}"')      # &, \" … du JSON de la page
        except Exception:
            pass
        videos.append((match.group(1), title))
        if len(videos) >= limit:
            break
    return videos


def pick_video(query: str, videos: list):
    """(identifiant, titre) : la première vidéo dont le titre contient tous les
    mots de la demande (espaces ignorés : « Don kangni » = « Donkangni »),
    sinon la première. Le 1er résultat pour « Santo Donkangni » était un
    extrait de télé-réalité (test du 01/11/2026)."""
    words = [w for w in (_compact(x) for x in str(query).split())
             if len(w) >= 3 and w not in _NOT_TITLE]
    for video in videos:
        title = _compact(video[1])
        if words and all(w in title for w in words):
            return video
    return videos[0] if videos else None


def play_music(query: str) -> dict:
    """Joue sur YouTube la vidéo qui correspond à la demande, dans le
    navigateur par défaut. Avant : une recherche sur YouTube Music, qui
    n'est pas disponible dans tous les pays (« YouTube Music n'est pas
    disponible dans votre pays », 26/10/2026), et rien ne se lançait."""
    query = str(query or "").strip()
    if not query:
        return {"error": "Dis-moi quel titre, artiste ou genre jouer."}
    try:
        best = pick_video(query, search_videos(query))
    except Exception:
        best = None
    if not best:
        result = open_youtube(query)
        if result.get("success"):
            result["message"] = "Je n'ai pas trouvé de vidéo à lancer : j'ai ouvert la recherche YouTube."
        return result
    video_id, title = best
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        webbrowser.open(url)
    except Exception as e:
        return {"error": str(e)}
    return {"success": True, "titre": title, "url": url,
            "message": f"Lecture de « {title} » sur YouTube."}


# ── Pilotage du lecteur en cours ──────────────────────────────────────────────
_MEDIA_KEYS = {"pause": 0xB3, "play": 0xB3, "next": 0xB0, "previous": 0xB1}   # touches multimédia
_ACTION_ALIASES = {"stop": "pause", "reprendre": "play", "reprise": "play", "suivant": "next",
                   "suivante": "next", "precedent": "previous", "precedente": "previous"}
_DONE = {"pause": "Musique en pause.", "play": "Musique relancée.",
         "next": "Morceau suivant.", "previous": "Morceau précédent."}
_meter_types = None


def _meter_interfaces():
    """Interfaces COM du compteur de crête des haut-parleurs (Windows Core
    Audio), déclarées une fois : seul GetPeakValue sert."""
    global _meter_types
    if _meter_types is None:
        from ctypes import POINTER, c_float, c_uint, c_void_p
        from comtypes import COMMETHOD, GUID, HRESULT, IUnknown

        class IAudioMeterInformation(IUnknown):
            _iid_ = GUID("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")
            _methods_ = [COMMETHOD([], HRESULT, "GetPeakValue", (["out"], POINTER(c_float), "peak"))]

        class IMMDevice(IUnknown):
            _iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
            _methods_ = [COMMETHOD([], HRESULT, "Activate",
                                   (["in"], POINTER(GUID), "iid"), (["in"], c_uint, "clsctx"),
                                   (["in"], c_void_p, "params"),
                                   (["out"], POINTER(POINTER(IUnknown)), "interface"))]

        class IMMDeviceEnumerator(IUnknown):
            _iid_ = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
            _methods_ = [
                COMMETHOD([], HRESULT, "EnumAudioEndpoints", (["in"], c_uint, "flow"),
                          (["in"], c_uint, "mask"), (["out"], POINTER(c_void_p), "devices")),
                COMMETHOD([], HRESULT, "GetDefaultAudioEndpoint", (["in"], c_uint, "flow"),
                          (["in"], c_uint, "role"), (["out"], POINTER(POINTER(IMMDevice)), "device")),
            ]
        _meter_types = (IAudioMeterInformation, IMMDeviceEnumerator)
    return _meter_types


def audio_playing(samples: int = 8, interval: float = 0.05):
    """True si un son sort des haut-parleurs (crête > 1 %, mesurée jusqu'à
    0,4 s), False sinon, None si on ne peut pas le savoir."""
    try:
        import comtypes
        from ctypes import byref
        meter_type, enumerator_type = _meter_interfaces()
        comtypes.CoInitialize()
        enumerator = comtypes.CoCreateInstance(
            comtypes.GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}"), enumerator_type, comtypes.CLSCTX_ALL)
        device = enumerator.GetDefaultAudioEndpoint(0, 1)          # sortie, multimédia
        meter = device.Activate(byref(meter_type._iid_), comtypes.CLSCTX_ALL, None).QueryInterface(meter_type)
        for _ in range(samples):
            if meter.GetPeakValue() > 0.01:
                return True
            time.sleep(interval)
        return False
    except Exception:
        return None


def _press_media_key(vk: int) -> None:
    import ctypes
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, 2, 0)                                 # touche relâchée


def control_music(action: str = "pause") -> dict:
    """Pause, reprise, morceau suivant ou précédent du lecteur en cours.
    Pause et reprise sont la même touche : on vérifie d'abord si un son sort,
    pour ne pas relancer une musique qu'on voulait arrêter."""
    action = str(action or "pause").strip().lower()
    action = _ACTION_ALIASES.get(action, action)
    if action not in _MEDIA_KEYS:
        return {"error": f"Action inconnue : {action} (pause, play, next ou previous)."}
    if action in ("pause", "play"):
        playing = audio_playing()
        if action == "pause" and playing is False:
            return {"success": True, "message": "Aucune musique en cours."}
        if action == "play" and playing is True:
            return {"success": True, "message": "La musique joue déjà."}
    try:
        _press_media_key(_MEDIA_KEYS[action])
    except Exception as e:
        return {"error": str(e)}
    return {"success": True, "message": _DONE[action]}


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
