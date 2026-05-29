import urllib.request
import json


def get_weather(location: str = "auto") -> dict:
    """
    Météo via wttr.in — gratuit, sans clé API.
    location : ville (ex: 'Paris'), 'auto' = géolocalisation automatique
    """
    try:
        loc  = "" if location.lower() in ("auto", "ici", "here") else location.replace(" ", "+")
        url  = f"https://wttr.in/{loc}?format=j1&lang=fr"
        req  = urllib.request.Request(url, headers={"User-Agent": "AmahAgent/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=8).read())

        cur  = data["current_condition"][0]
        area = data["nearest_area"][0]
        city = area["areaName"][0]["value"]
        country = area["country"][0]["value"]

        # Prévisions J+1 et J+2
        forecasts = []
        for day in data["weather"][:3]:
            forecasts.append({
                "date":      day["date"],
                "max":       day["maxtempC"] + "°C",
                "min":       day["mintempC"] + "°C",
                "condition": day["hourly"][4]["weatherDesc"][0]["value"],
            })

        return {
            "success":      True,
            "ville":        f"{city}, {country}",
            "temperature":  cur["temp_C"] + "°C",
            "ressenti":     cur["FeelsLikeC"] + "°C",
            "humidite":     cur["humidity"] + "%",
            "vent":         cur["windspeedKmph"] + " km/h",
            "condition":    cur["weatherDesc"][0]["value"],
            "previsions":   forecasts,
        }
    except Exception as e:
        return {"error": f"Impossible de récupérer la météo : {e}"}


def get_weather_simple(location: str = "auto") -> dict:
    """Version courte — une seule ligne de résumé."""
    try:
        loc = "" if location.lower() in ("auto", "ici") else location.replace(" ", "+")
        url = f"https://wttr.in/{loc}?format=3"
        req = urllib.request.Request(url, headers={"User-Agent": "AmahAgent/1.0"})
        result = urllib.request.urlopen(req, timeout=8).read().decode()
        return {"success": True, "meteo": result.strip()}
    except Exception as e:
        return {"error": str(e)}
