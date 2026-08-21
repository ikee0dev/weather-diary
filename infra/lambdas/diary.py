"""The diary entry: real weather in, one new gallery entry out. Runs on an
EventBridge schedule - unattended by design, the whole point of the app.

Pipeline: weather.fetch() (real Open-Meteo reading) -> descriptors.derive()
(honest visual/mood vocabulary) -> artgen.render() (procedural SVG, no
foundation model - see artgen.py's docstring for why) -> caption_model
.generate_caption() (Gemini, the one AI call in the chain). A caption
failure does not lose the picture: the entry still gets stored with an
honest caption_error, same degrade-visibly rule as the other two apps.
"""

import json
import os
from datetime import datetime, timezone

import boto3

import artgen
import caption_model
import descriptors
import weather

TABLE_NAME = os.environ["GALLERY_TABLE"]

_table = boto3.resource("dynamodb").Table(TABLE_NAME)


def handler(event, context):
    w = weather.fetch()
    d = descriptors.derive(w)
    svg = artgen.render(w, d)

    caption = None
    caption_error = None
    model = None
    try:
        out = caption_model.generate_caption(w, d)
        caption, model = out["caption"], out["model"]
    except caption_model.CaptionError as exc:
        caption_error = str(exc)

    now = datetime.now(timezone.utc)
    record = {
        "generated_at": now.isoformat(timespec="seconds"),
        "weather": w,
        "descriptors": d["levels"],
        "svg": svg,
        "caption": caption,
        "caption_error": caption_error,
        "model": model,
    }

    body = json.dumps(record)
    _table.put_item(Item={"pk": "ENTRY", "sk": record["generated_at"], "body": body})
    _table.put_item(Item={"pk": "LATEST", "sk": "LATEST", "body": body})
    return {"generated_at": record["generated_at"], "condition": d["condition"],
            "caption": caption, "caption_error": caption_error}
