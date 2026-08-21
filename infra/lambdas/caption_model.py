"""The caption seam: real weather in, one short first-person line out.

Gemini writes it, key pulled from Secrets Manager, structured JSON so the
Lambda never has to scrape prose out of a chat response. There is no
canned fallback line: if the model is unreachable the picture still ships,
just without words under it, rather than a caption that lies about having
been written by anything.
"""

import json
import os
import urllib.request
from typing import Optional

MODEL_ID = os.environ.get("MODEL_ID", "gemini-flash-latest")
MODEL_FALLBACKS = [m.strip() for m in
                   os.environ.get("MODEL_FALLBACKS", "gemini-3.5-flash-lite").split(",")
                   if m.strip()]
GEMINI_SECRET_NAME = os.environ.get("GEMINI_SECRET_NAME", "weather-diary/gemini")
_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_PRIMARY_TIMEOUT_S = int(os.environ.get("GEMINI_TIMEOUT_S", "18"))
_FALLBACK_TIMEOUT_S = int(os.environ.get("GEMINI_FALLBACK_TIMEOUT_S", "8"))

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"caption": {"type": "string"}},
    "required": ["caption"],
}

_PROMPT = """\
You are today's diary entry for the sky over {city}, written the instant
after it was painted.

Real conditions right now:
- {temperature_c} C, feels {warmth}
- sky is {cloudiness} ({cloud_cover_pct}% real cloud cover)
- {condition}, {rain} rain ({precipitation_mm} mm)
- wind is {wind} at {wind_speed_kmh} km/h
- it is currently {daynight} in {city}

Write one short first-person caption, as if the sky itself is describing
this exact moment for its own diary. One or two sentences. No hashtags, no
emoji, no mention of temperature units or percentages - translate the
numbers into how it feels, not what they measure. Grounded and specific to
these real conditions, never generic.
"""


def _api_key() -> Optional[str]:
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    try:
        import boto3
        raw = boto3.client("secretsmanager").get_secret_value(
            SecretId=GEMINI_SECRET_NAME)["SecretString"]
        return json.loads(raw).get("api_key")
    except Exception:  # noqa: BLE001 - no secret / no access -> caller errors honestly
        return None


def _call_gemini(prompt: str, key: str, model_id: str, timeout: int) -> dict:
    url = f"{_API_BASE}/{model_id}:generateContent?key={key}"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _RESPONSE_SCHEMA,
            "temperature": 0.9,
        },
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        payload = json.load(r)
    return json.loads(payload["candidates"][0]["content"]["parts"][0]["text"])


class CaptionError(Exception):
    """Every model attempt failed; the caller should say so honestly."""


def generate_caption(weather: dict, derived: dict) -> dict:
    """Turn real weather + derived vocabulary into a caption. Returns
    {caption, model}. Raises CaptionError if no model produced output."""
    key = _api_key()
    if not key:
        raise CaptionError("no Gemini key available")

    prompt = _PROMPT.format(
        city=weather["city"],
        temperature_c=weather["temperature_c"],
        warmth=derived["warmth"],
        cloudiness=derived["cloudiness"],
        cloud_cover_pct=weather["cloud_cover_pct"],
        condition=derived["condition"],
        rain=derived["rain"],
        precipitation_mm=weather["precipitation_mm"],
        wind=derived["wind"],
        wind_speed_kmh=weather["wind_speed_kmh"],
        daynight="day" if derived["is_day"] else "night",
    )

    last_err: Exception | str = "no models configured"
    for idx, model_id in enumerate([MODEL_ID, *MODEL_FALLBACKS]):
        timeout = _PRIMARY_TIMEOUT_S if idx == 0 else _FALLBACK_TIMEOUT_S
        try:
            raw = _call_gemini(prompt, key, model_id, timeout)
        except Exception as exc:  # noqa: BLE001 - try the next model
            last_err = exc
            continue
        caption = (raw.get("caption") or "").strip()
        if caption:
            return {"caption": caption, "model": model_id}
        last_err = "model returned an empty caption"
    reason = type(last_err).__name__ if isinstance(last_err, Exception) else str(last_err)
    raise CaptionError(f"all models failed ({reason})")
