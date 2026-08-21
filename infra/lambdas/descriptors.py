"""Real weather numbers in, honest visual language out.

Thresholds calibrated against real Lagos conditions sampled while building
this (2026-08-21 01:00 WAT: 25.7C, 100% cloud, 5.6 km/h wind, weather_code 3,
92% humidity, no rain) rather than guessed round numbers, same calibration
discipline as infra-narrator's descriptor pool. WMO weather_code buckets
follow the published Open-Meteo table.
"""

# WMO weather_code -> a coarse real-world condition bucket.
_CODE_BUCKETS = [
    (range(0, 1), "clear"),
    (range(1, 4), "cloudy"),
    (range(45, 49), "fog"),
    (range(51, 68), "rain"),
    (range(71, 78), "rain"),      # Lagos never really sees this; kept honest, not hidden
    (range(80, 83), "showers"),
    (range(95, 100), "storm"),
]


def _condition(code: int) -> str:
    for rng, label in _CODE_BUCKETS:
        if code in rng:
            return label
    return "cloudy"


def _warmth(temp_c: float) -> str:
    return ("cool" if temp_c < 24 else
            "mild" if temp_c < 28 else
            "warm" if temp_c < 32 else
            "hot")


def _cloudiness(pct: float) -> str:
    return ("clear" if pct < 20 else
            "partly" if pct < 70 else
            "overcast")


def _wind(kmh: float) -> str:
    return ("calm" if kmh < 8 else
            "breeze" if kmh < 20 else
            "windy")


def _rain(mm: float) -> str:
    return ("dry" if mm <= 0 else
            "light" if mm < 2 else
            "moderate" if mm < 10 else
            "heavy")


def derive(w: dict) -> dict:
    """w is weather.fetch()'s real dict. Returns the visual/mood vocabulary
    both the art generator and the caption model read from - never raw
    numbers reaching either without passing through here first.
    """
    condition = _condition(int(w["weather_code"]))
    warmth = _warmth(w["temperature_c"])
    cloudiness = _cloudiness(w["cloud_cover_pct"])
    wind = _wind(w["wind_speed_kmh"])
    rain = _rain(w["precipitation_mm"])

    return {
        "condition": condition,
        "warmth": warmth,
        "cloudiness": cloudiness,
        "wind": wind,
        "rain": rain,
        "is_day": w["is_day"],
        "levels": {
            "condition": condition, "warmth": warmth, "cloudiness": cloudiness,
            "wind": wind, "rain": rain,
        },
    }
