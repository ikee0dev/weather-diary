# Architecture

One CDK stack (`wd-dev`), not three — see `infra/lib/weather-diary-stack.ts`
for the reasoning. A CloudFront-proxied, IAM-authed Lambda Function URL was
the original plan for the read route (no API Gateway, no CORS surface at
all); it hit a real, unresolved `AccessDeniedException` between CloudFront's
Origin Access Control and Lambda Function URLs despite a textbook-correct
config on both sides, documented in `BUILD_LOG.md` step 8. The read route
is a one-resource API Gateway REST API instead — the same building block
already proven reliable in this series' other two entries.

```mermaid
sequenceDiagram
    participant EB as EventBridge (rate: 6h)
    participant Diary as DiaryFn (Lambda)
    participant OM as Open-Meteo
    participant Art as artgen.py (in-process)
    participant Gem as Gemini
    participant DB as DynamoDB (wd-gallery)
    participant Visitor
    participant APIGW as API Gateway (GET /gallery)
    participant Gallery as GalleryFn (Lambda)

    Note over EB,DB: unattended, no human involved
    EB->>Diary: invoke (no input)
    Diary->>OM: GET current weather (Lagos)
    OM-->>Diary: real temp, wind, cloud, rain, is_day
    Diary->>Diary: conditions.read() -> 5-word vocabulary
    Diary->>Art: render(weather, vocabulary)
    Art-->>Diary: SVG string (no model call)
    Diary->>Gem: caption prompt (real numbers, real words)
    Gem-->>Diary: one-line caption (or Diary catches an honest error)
    Diary->>DB: put_item pk=ENTRY  + put_item pk=LATEST

    Note over Visitor,Gallery: hours later, on its own schedule
    Visitor->>APIGW: GET /gallery (via CloudFront -> S3 static site -> fetch)
    APIGW->>Gallery: invoke
    Gallery->>DB: query pk=ENTRY, newest first
    DB-->>Gallery: up to 60 real entries
    Gallery-->>Visitor: JSON, SVGs inline, no image files anywhere
```

## Why this shape

- **One stack.** The app has exactly one table, one scheduled writer, one
  public reader, one static site. Three stacks (data/api/hosting) would
  only exist to hand exports between each other for no functional reason
  at this size.
- **No S3 image bucket.** Each picture is a few KB of SVG markup, stored
  inline as a DynamoDB attribute and injected straight into the DOM. A
  bucket, an Origin Access Control, and presigned URLs would all exist to
  solve a storage problem this app doesn't have.
- **No foundation model for the art.** See `artgen.py`'s docstring: Amazon
  Bedrock hit a real account-level throttle, confirmed across two models,
  so the picture is built by code reading `conditions.py`'s five-word
  vocabulary directly. Gemini still writes the caption — that call has
  never been throttled.
- **API Gateway, after all.** Tried to remove it too (see step 8 in
  `BUILD_LOG.md`); the attempt failed for reasons outside this app's
  control, not because the idea was wrong.

## AWS services in play

Lambda (write path + read path), EventBridge (the schedule), DynamoDB (the
one table), API Gateway (the one route), Secrets Manager (the Gemini key),
S3 + CloudFront (the static frontend only — no data lives in S3 here).
