"""Free Agricultural Weather & Advisory API integration using Open-Meteo.
No API key required, 100% free and open for public and agricultural use.
"""

import datetime
import json
import urllib.request

# In-memory cache for weather data (10 minute TTL) to ensure ultra-smooth performance
_WEATHER_CACHE = {
    "data": None,
    "timestamp": None,
}


def get_agri_weather(lat=28.14, lon=77.32):
    """Fetch real-time weather and agricultural advisory for farmers."""
    now = datetime.datetime.now()
    if (
        _WEATHER_CACHE["data"]
        and _WEATHER_CACHE["timestamp"]
        and (now - _WEATHER_CACHE["timestamp"]).total_seconds() < 600
    ):
        return _WEATHER_CACHE["data"]

    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        "&daily=precipitation_probability_max,temperature_2m_max,temperature_2m_min"
        "&timezone=Asia%2FKolkata&forecast_days=1"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "KisanRoute/1.0"})
        with urllib.request.urlopen(req, timeout=3.5) as response:
            raw = json.loads(response.read().decode("utf-8"))

        current = raw.get("current", {})
        daily = raw.get("daily", {})

        temp = round(current.get("temperature_2m", 28.0), 1)
        humidity = current.get("relative_humidity_2m", 55)
        wind = current.get("wind_speed_10m", 8.0)
        rain_prob = daily.get("precipitation_probability_max", [15])[0]
        max_temp = daily.get("temperature_2m_max", [temp + 2])[0]
        min_temp = daily.get("temperature_2m_min", [temp - 4])[0]

        # Weather condition description & advisory
        if rain_prob >= 60:
            condition = "बारिश की संभावना (Rain Likely)"
            icon = "🌧️"
            advisory_hi = "आज बारिश की संभावना अधिक है। कटी हुई फसल को ढक कर रखें और मंडी परिवहन तिरपाल से सुरक्षित करें।"
            advisory_en = "High chance of rain. Keep harvested crops covered and protect open transport with tarpaulins."
        elif rain_prob >= 35:
            condition = "बादल छाए रहेंगे (Partly Cloudy)"
            icon = "⛅"
            advisory_hi = "हल्के बादल छाए रहेंगे। सामान्य सिंचाई और कृषि कार्य जारी रख सकते हैं।"
            advisory_en = "Partly cloudy skies. Normal irrigation and field work can continue."
        else:
            condition = "मौसम साफ व अनुकूल (Clear & Sunny)"
            icon = "☀️"
            advisory_hi = "मौसम पूरी तरह साफ है। फसल कटाई, थ्रेशिंग और मंडी तक परिवहन के लिए आदर्श समय है।"
            advisory_en = "Clear skies. Ideal conditions for harvesting, threshing, and transit to mandi."

        result = {
            "success": True,
            "temp": temp,
            "max_temp": max_temp,
            "min_temp": min_temp,
            "humidity": humidity,
            "wind_speed": wind,
            "rain_prob": rain_prob,
            "condition": condition,
            "icon": icon,
            "advisory_hi": advisory_hi,
            "advisory_en": advisory_en,
            "location": "पलवल / दिल्ली-एनसीआर क्षेत्र (NCR Agri Belt)",
            "updated_at": now.strftime("%I:%M %p"),
        }
        _WEATHER_CACHE["data"] = result
        _WEATHER_CACHE["timestamp"] = now
        return result

    except Exception:
        # Fallback offline-ready weather data
        return {
            "success": False,
            "temp": 29.5,
            "max_temp": 32.0,
            "min_temp": 24.0,
            "humidity": 58,
            "wind_speed": 7.5,
            "rain_prob": 20,
            "condition": "मौसम साफ व अनुकूल (Clear Weather)",
            "icon": "🌤️",
            "advisory_hi": "मौसम साफ है। फसल कटाई और मंडी में बिक्री के लिए अनुकूल समय है।",
            "advisory_en": "Clear weather. Suitable for harvesting and transportation to mandi.",
            "location": "पलवल / दिल्ली-एनसीआर क्षेत्र (NCR Agri Belt)",
            "updated_at": now.strftime("%I:%M %p"),
        }
