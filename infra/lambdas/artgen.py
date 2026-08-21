"""Procedural SVG art, built directly from real weather numbers.

No foundation model draws this. Amazon Bedrock (Nova Canvas) was the first
choice and the code for it was written, but this account hit the same real
"too many tokens per day" account-level throttle already logged in
standup-brief's build history - confirmed on both an image and a text
model, so it is not a Nova Canvas quirk. Rather than fake the picture or
wait on a support case that will not resolve inside a weekend, this file
just draws conclusions from conditions.read()'s five real words itself:
each one maps deterministically to a shape count, a color, an angle -
nothing invented, nothing asked of a model. A `random.Random` seeded from
the real observation timestamp adds variety without breaking
reproducibility - the same real minute always paints the same picture.

Canvas is a fixed 800x500 viewBox: sky gradient, sun or moon, clouds, rain,
wind, and a small silhouette skyline to anchor "a diary of the sky over one
city" rather than an abstract gradient.
"""

import math
import random

W, H = 800, 500

# (is_day) x warmth -> (top, bottom) sky colors. Warmth shifts the palette
# toward amber/rose; night always reads as night, day always as day - the
# real is_day flag from Open-Meteo, not a guessed hour cutoff.
_SKY = {
    (True,  "cool"): ("#bcd8e8", "#eef6f5"),
    (True,  "mild"): ("#8fc7e0", "#dff1e8"),
    (True,  "warm"): ("#6fb6df", "#ffe9c2"),
    (True,  "hot"):  ("#4f9fd6", "#ffd9a0"),
    (False, "cool"): ("#0c1730", "#26314f"),
    (False, "mild"): ("#0f1a33", "#2c2f52"),
    (False, "warm"): ("#1a1233", "#3a2350"),
    (False, "hot"):  ("#241030", "#4a1f3d"),
}

_CLOUD_TINT = {"clear": "#ffffff", "cloudy": "#e7ecef",
               "rain": "#9aa6ad", "showers": "#9aa6ad",
               "storm": "#5e6a72", "fog": "#dfe4e6"}

_SUN_COLOR = "#ffd76a"
_MOON_COLOR = "#eef0f7"
_SKYLINE_DAY = "#1c2b3a"
_SKYLINE_NIGHT = "#050810"


def _hour_fraction(iso_time: str) -> float:
    """0.0 at 00:00 local, 1.0 at 24:00 - real local hour from the real
    Open-Meteo timestamp, so the sun/moon position is honestly derived."""
    hhmm = iso_time.split("T")[1]
    h, m = hhmm.split(":")
    return (int(h) + int(m) / 60.0) / 24.0


def render(weather: dict, derived: dict) -> str:
    rnd = random.Random(weather["time"])  # real timestamp seeds real variety
    is_day = derived["is_day"]
    top, bottom = _SKY[(is_day, derived["warmth"])]
    cloud_tint = _CLOUD_TINT.get(derived["condition"], "#e7ecef")
    skyline = _SKYLINE_DAY if is_day else _SKYLINE_NIGHT

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="Georgia, serif">',
        f'<title>{weather["city"]} sky, {weather["time"]}</title>',
        f'<desc>{weather["temperature_c"]}C, {weather["cloud_cover_pct"]}% cloud, '
        f'{weather["wind_speed_kmh"]}km/h wind, {weather["precipitation_mm"]}mm rain, '
        f'condition={derived["condition"]}</desc>',
        '<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">',
        f'<stop offset="0%" stop-color="{top}"/>',
        f'<stop offset="100%" stop-color="{bottom}"/>',
        '</linearGradient></defs>',
        f'<rect width="{W}" height="{H}" fill="url(#sky)"/>',
    ]

    # Sun/moon: real local hour places it on a simple daytime/nighttime arc,
    # hidden increasingly behind heavy cloud - clouds occlude honestly
    # rather than the disc just vanishing at a hardcoded cloud percentage.
    frac = _hour_fraction(weather["time"])
    arc = math.sin(math.pi * ((frac - (0.25 if is_day else 0.75)) / 0.5)) if (
        (is_day and 0.25 <= frac <= 0.75) or (not is_day and (frac >= 0.75 or frac <= 0.25))
    ) else 0.15
    cx = 80 + frac * (W - 160)
    cy = H * 0.55 - max(arc, 0.1) * H * 0.42
    disc_color = _SUN_COLOR if is_day else _MOON_COLOR
    disc_opacity = max(0.15, 1 - weather["cloud_cover_pct"] / 130)
    parts.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="34" fill="{disc_color}" '
                 f'opacity="{disc_opacity:.2f}"/>')

    # Clouds: count and opacity scale with the real cloud_cover percentage.
    n_clouds = round(derived_cloud_count(weather["cloud_cover_pct"]))
    for _ in range(n_clouds):
        ccx = rnd.uniform(0, W)
        ccy = rnd.uniform(40, H * 0.55)
        scale = rnd.uniform(0.6, 1.4)
        op = 0.35 + 0.5 * (weather["cloud_cover_pct"] / 100)
        parts.append(_cloud_puff(ccx, ccy, scale, cloud_tint, op))

    # Rain: only if there is real precipitation, angled by the real wind
    # direction, count scaling with real intensity.
    if weather["precipitation_mm"] > 0:
        n_drops = min(140, round(20 + weather["precipitation_mm"] * 18))
        angle = (weather["wind_direction_deg"] + 180) % 360
        dx = math.sin(math.radians(angle)) * 18
        for _ in range(n_drops):
            x = rnd.uniform(0, W)
            y = rnd.uniform(0, H * 0.85)
            parts.append(
                f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x + dx:.0f}" y2="{y + 22:.0f}" '
                f'stroke="#bcd6e8" stroke-width="1.4" opacity="0.55"/>')

    # Wind: soft swoosh strokes, count scaling with real wind speed.
    n_wind = min(10, round(weather["wind_speed_kmh"] / 3))
    for i in range(n_wind):
        y = rnd.uniform(30, H * 0.5)
        x0 = rnd.uniform(0, W * 0.7)
        length = rnd.uniform(40, 110)
        parts.append(
            f'<path d="M{x0:.0f} {y:.0f} q {length/2:.0f} -8 {length:.0f} 0" '
            f'stroke="#ffffff" stroke-width="1.2" fill="none" opacity="0.3"/>')

    # A small silhouette skyline anchors this as one city's diary, not an
    # abstract gradient. Shapes are fixed per building slot but heights get
    # real-seeded jitter for a touch of life without losing the anchor.
    n_bldg = 11
    bw = W / n_bldg
    for i in range(n_bldg):
        bh = 70 + rnd.uniform(0, 90) + (30 if i % 3 == 0 else 0)
        parts.append(f'<rect x="{i*bw:.0f}" y="{H-bh:.0f}" width="{bw*0.82:.0f}" '
                     f'height="{bh:.0f}" fill="{skyline}"/>')

    parts.append('</svg>')
    return "\n".join(parts)


def derived_cloud_count(pct: float) -> float:
    return max(0, pct / 9)


def _cloud_puff(cx: float, cy: float, scale: float, tint: str, opacity: float) -> str:
    r1, r2, r3 = 28 * scale, 20 * scale, 24 * scale
    return (
        f'<g opacity="{opacity:.2f}">'
        f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{r1:.0f}" ry="{r1*0.6:.0f}" fill="{tint}"/>'
        f'<ellipse cx="{cx-r1*0.7:.0f}" cy="{cy+4:.0f}" rx="{r2:.0f}" ry="{r2*0.6:.0f}" fill="{tint}"/>'
        f'<ellipse cx="{cx+r1*0.7:.0f}" cy="{cy+4:.0f}" rx="{r3:.0f}" ry="{r3*0.6:.0f}" fill="{tint}"/>'
        f'</g>'
    )
