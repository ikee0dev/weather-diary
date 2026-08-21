"""Real weather in: Open-Meteo's current-conditions endpoint, no API key.

Every number the descriptor pool and the art generator use downstream comes
from here, unmodified. Nothing about the sky is invented.
"""

import json
import os
import urllib.request

LAT = float(os.environ.get("WD_LAT", "6.5244"))   # Lagos, Nigeria, default
LON = float(os.environ.get("WD_LON", "3.3792"))
TZ = os.environ.get("WD_TZ", "Africa/Lagos")
CITY = os.environ.get("WD_CITY", "Lagos")

_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}&timezone={TZ}"
    "&current=temperature_2m,wind_speed_10m,wind_direction_10m,"
    "weather_code,cloud_cover,precipitation,relative_humidity_2m,is_day"
)


class WeatherError(Exception):
    """The real feed didn't answer; the caller should say so honestly."""


def fetch(timeout: int = 10) -> dict:
    try:
        with urllib.request.urlopen(_URL, timeout=timeout) as r:
            payload = json.load(r)
    except Exception as exc:  # noqa: BLE001 - caller decides how to fail
        raise WeatherError(f"open-meteo fetch failed: {type(exc).__name__}: {exc}") from exc

    c = payload["current"]
    return {
        "city": CITY,
        "time": c["time"],
        "temperature_c": c["temperature_2m"],
        "wind_speed_kmh": c["wind_speed_10m"],
        "wind_direction_deg": c["wind_direction_10m"],
        "weather_code": c["weather_code"],
        "cloud_cover_pct": c["cloud_cover"],
        "precipitation_mm": c["precipitation"],
        "humidity_pct": c["relative_humidity_2m"],
        "is_day": bool(c["is_day"]),
    }
