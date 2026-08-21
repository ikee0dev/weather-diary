# Weather Diary

A sky that paints and writes about itself, on its own, every six hours.

Weather Diary reads real current conditions for Lagos, Nigeria, turns them
into a small honest visual vocabulary, procedurally paints an SVG sky from
that vocabulary, and asks Gemini to write a one-line first-person caption
for the moment — all unattended, on an EventBridge schedule. Nobody has to
open the page for a new entry to exist.

Built for the AWS Builder Center "Set Your Creative App Free" weekend
challenge (Aug 21-24, 2026).

## Why the art isn't AI-generated

The first design called for Amazon Bedrock (Nova Canvas) to paint the sky.
On this account, both Nova Canvas and a plain Bedrock text model returned
`ThrottlingException: Too many tokens per day` — the exact same
account-level daily allowance issue already documented in a sibling
project's build history (`debugging-saga`'s showcase story about
`standup-brief`), confirmed here across two different models and
modalities, so it isn't a Nova Canvas quirk. Rather than fake the picture,
the art is generated the same way every descriptor pool in this series
already works: real numbers mapped deterministically into a visual
vocabulary, nothing invented. Gemini still writes the caption — that part
of the account has never been throttled.

## How it works

```
EventBridge (every 6h) ──> Lambda
                              │
                              ├──> Open-Meteo (real weather, no key)
                              ├──> descriptors.py (numbers -> honest vocabulary)
                              ├──> artgen.py (procedural SVG, no model)
                              └──> Gemini (one-line caption)
                                       │
                                       └──> DynamoDB (the growing gallery)

frontend <── API Gateway <── GET /gallery ──┘
```

- **Lambda (Python 3.12):** weather fetch, descriptor derivation, SVG art,
  caption generation
- **Amazon EventBridge:** the schedule that makes this an agent, not a button
- **Amazon DynamoDB:** the gallery, no TTL — it's meant to grow
- **Amazon API Gateway:** one read-only `GET /gallery`
- **AWS Secrets Manager:** the Gemini key
- **S3 + CloudFront:** static frontend
- **Google Gemini:** the one AI call, the caption

## Status

Live: https://d24q0uqc2v91xq.cloudfront.net

```
curl https://72cc0ff9q4.execute-api.us-east-1.amazonaws.com/dev/gallery
```

## Infra

CDK (TypeScript), three stacks: data (gallery table), api, hosting.

```
cd infra
npm install
npx cdk deploy --all
```

Teardown: `npx cdk destroy --all`.
