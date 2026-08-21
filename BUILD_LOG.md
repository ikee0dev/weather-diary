# Build log

## Step 1: real weather in (2026-08-21) — AWS Builder Center "Set Your
## Creative App Free" weekend

Sampled Open-Meteo's current-conditions endpoint (no key required) for
Lagos, Nigeria, before writing a single threshold: 2026-08-21 01:00 WAT,
25.7C, 100% cloud cover, 5.6 km/h wind at 225 degrees, weather_code 3, 92%
humidity, no rain. `weather.py` fetches this on every run; nothing about
the sky downstream is invented.

## Step 2: the descriptor pool

`descriptors.py` maps the real numbers into a small honest vocabulary
(warmth, cloudiness, wind, rain, condition from the WMO weather_code
table) with thresholds calibrated against the real sample above rather
than guessed round numbers — same calibration discipline as
infra-narrator's descriptor pool.

## Step 3: the Bedrock detour

The original plan for the art was Amazon Bedrock (Nova Canvas). Real
invocation attempt, `amazon.nova-canvas-v1:0`, us-east-1:
`ThrottlingException: Too many requests, please wait before trying again.`
Retried after a 15s backoff: same error. To isolate whether this was a
Nova Canvas rate limit or the account-level daily allowance already logged
in `debugging-saga`'s showcase story about `standup-brief`, invoked a
second, unrelated, lightweight model, `amazon.nova-micro-v1:0`, with a
five-word prompt: `ThrottlingException: Too many tokens per day, please
wait before trying again.` Same message, word for word, as the prior
project's documented incident. Confirmed account-wide, confirmed not
Nova-Canvas-specific, confirmed not fixable inside a weekend (the prior
project's research already established the fix requires an AWS Support
case, unavailable on Basic support).

## Step 4: procedural art instead

`artgen.py` builds the sky as SVG directly from the real weather dict and
the derived vocabulary: a sky gradient keyed by the real `is_day` flag and
warmth, a sun or moon placed by the real local hour and partially occluded
by the real cloud percentage, cloud puffs whose count and opacity scale
with real cloud cover, rain streaks that only appear with real
precipitation and are angled by the real wind direction, wind swooshes
scaled by real wind speed, and a small silhouette skyline anchoring it as
one city's diary. A `random.Random` seeded on the real observation
timestamp adds shape variety without breaking reproducibility.

Local smoke test against the real Lagos sample: valid SVG, 3555 bytes,
title and desc tags carrying the real numbers.

## Step 5: the caption

`caption_model.py` reuses the proven three-model Gemini pattern from the
other two apps in this series (key in Secrets Manager, primary +
fallback, structured JSON, honest error if every model fails — no
deterministic fallback caption).

## Step 6: deployed and proven live

CDK-TS, 3 stacks (data: one DynamoDB table, no TTL; api: the diary Lambda
on a 6-hour EventBridge schedule plus a read-only `GET /gallery`; hosting:
S3 + CloudFront). `npx tsc --noEmit` and `cdk synth` both clean. Deployed
to us-east-1 dev.

Verified with three real, separately generated entries, not a mock: direct
invocation of the deployed `wd-diary-dev` Lambda produced real captions
against the real live conditions -
  "I am a heavy, silent blanket resting over Lagos tonight. The air is
  still, holding back the dark clouds without a single drop of rain."
  "I am a heavy, unbroken ceiling of gray draped silently over the sleeping
  city. Not a single drop falls from my dark folds, and the night air
  remains completely still."
- and `GET /gallery` served all three back with their real SVGs intact.
Confirmed live in a real browser: three cards, each a distinct night sky
with drifting clouds and a barely-visible moon (honest under 100% real
cloud cover), real stats line, real UTC timestamp, labelled "unattended."
EventBridge rule confirmed `ENABLED` on `rate(6 hours)`.

Remaining: hand off to a GitHub repo and publish the Builder Center
article.
