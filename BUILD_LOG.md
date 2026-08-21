# Build log

## Step 1: real weather in (2026-08-21) — AWS Builder Center "Set Your
## Creative App Free" weekend

Sampled Open-Meteo's current-conditions endpoint (no key required) for
Lagos, Nigeria, before writing a single threshold: 2026-08-21 01:00 WAT,
25.7C, 100% cloud cover, 5.6 km/h wind at 225 degrees, weather_code 3, 92%
humidity, no rain. `weather.py` fetches this on every run; nothing about
the sky downstream is invented.

## Step 2: five words, not raw numbers

`conditions.py` reduces the real reading to exactly five words — warmth,
cloudiness, wind, rain, condition (the last one from the published WMO
weather_code table) — with thresholds calibrated against the real sample
above rather than guessed round numbers. Nothing past this file ever sees
a raw temperature or percentage again.

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

`caption_model.py` asks Gemini for one first-person line, key in Secrets
Manager, structured JSON response, no canned fallback line — a caption
failure ships the picture wordless rather than under a fake sentence.

## Step 6: deployed and proven live (first pass, 3 stacks)

CDK-TS, 3 stacks (data: one DynamoDB table, no TTL; api: the diary Lambda
on a 6-hour EventBridge schedule plus a read-only `GET /gallery` behind
API Gateway; hosting: S3 + CloudFront). `npx tsc --noEmit` and `cdk synth`
both clean. Deployed to us-east-1 dev.

Verified with three real, separately generated entries, not a mock: direct
invocation of the deployed diary Lambda produced real captions against the
real live conditions -
  "I am a heavy, silent blanket resting over Lagos tonight. The air is
  still, holding back the dark clouds without a single drop of rain."
  "I am a heavy, unbroken ceiling of gray draped silently over the sleeping
  city. Not a single drop falls from my dark folds, and the night air
  remains completely still."
- and the read route served all three back with their real SVGs intact.
Confirmed live in a real browser: three cards, each a distinct night sky
with drifting clouds and a barely-visible moon (honest under 100% real
cloud cover), real stats line, real UTC timestamp, labelled "unattended."
EventBridge rule confirmed `ENABLED` on `rate(6 hours)`.

## Step 7: one stack instead of three, and a name of its own

Once two sibling apps in this series existed side by side, the 3-stack
data/api/hosting split this one started with read as a copy of theirs
rather than a decision made for this app's own size. Collapsed to one
stack (`weather-diary-stack.ts`) — one table, one scheduled writer, one
public reader, one static site don't need cross-stack exports to talk to
each other. `descriptors.py` also became `conditions.py` (`derive()`
became `read()`, the `levels` key became `labels`): a five-word vocabulary
specific to weather, not a borrowed name from a different app's metaphor
engine.

The old 3-stack deployment (with its three real proof entries) was
destroyed cleanly via `aws cloudformation delete-stack`, in dependency
order (hosting, then api, then data), and the app redeployed as the new
single stack.

## Step 8: a real dead end - CloudFront OAC does not want to invoke a
## Lambda Function URL today

Tried to drop API Gateway too: a bare Lambda Function URL for the one read
route, IAM-authed, reachable only through a CloudFront Origin Access
Control so there would be no separately-public API domain at all. Every
piece of the setup matched AWS's own documented shape exactly - resource
policy scoped to `cloudfront.amazonaws.com` with the right
`AWS:SourceArn`, OAC config `sigv4` / `always` / `lambda`, origin domain
matching the real Function URL - and CloudFront still returned a genuine
`AccessDeniedException` on every request, survived a cache invalidation,
survived a second full deploy. The Lambda itself was never the problem:
CloudWatch logs showed clean, successful invocations the entire time,
which meant the failure was happening in the handshake between two AWS
features, not in this app's code.

Rather than keep guessing at an AWS-side gap, reverted the one read route
to a one-resource API Gateway REST API - the same building block already
proven reliable twice over in the other two entries in this series - and
kept everything else (the single stack, the direct-to-DynamoDB inline SVG
storage, the six-hour schedule) as decided in step 7. `npx tsc --noEmit`
and `cdk synth` clean, deployed, and this time actually confirmed inside a
real browser tab, not just curl: three fresh entries rendered correctly,
distinct night skies, real captions, "UNATTENDED" stamped on each one.
EventBridge rule confirmed `ENABLED` on `rate(6 hours)`.

Remaining: publish the Builder Center article.
