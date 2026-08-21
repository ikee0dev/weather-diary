# Weather Diary

A sky that paints and writes about itself, on its own, every six hours.

Weather Diary reads Lagos's real current weather, reduces it to five honest
words (`conditions.py`), lets plain code turn those words into an SVG
picture (`artgen.py` — no image model involved), asks Gemini for a one-line
caption of the same real moment, and files the result into a gallery that
only ever grows. EventBridge does the asking; nobody has to open the page.

Built for the AWS Builder Center "Set Your Creative App Free" weekend
challenge (Aug 21-24, 2026). See `docs/architecture.md` for the full
diagram and `BUILD_LOG.md` for the Bedrock detour this app took to get
here.

## Why there's no AI-generated image

Amazon Bedrock's Nova Canvas was the original plan. First real call:
`ThrottlingException: Too many requests`. A second, unrelated Bedrock text
model, invoked purely to isolate the cause: `ThrottlingException: Too many
tokens per day` — the identical account-level daily allowance already
documented in a sibling project's history (`debugging-saga`'s showcase
story about `standup-brief`). Confirmed account-wide, confirmed not
fixable inside a weekend. So the picture is drawn by code instead: five
real words in, one deterministic SVG out. Gemini kept working the whole
time and still writes the caption.

## What's running

| Piece | Job |
|---|---|
| `DiaryFn` (Lambda) | Fetches real weather, derives conditions, paints the SVG, gets the caption, writes the entry. EventBridge calls it — nothing else does. |
| `GalleryFn` (Lambda, behind one API Gateway route) | The only public route: read every entry so far. |
| DynamoDB (`wd-gallery-dev`) | The growing gallery. No TTL. |
| S3 + CloudFront | The static frontend. |

A CloudFront-proxied, IAM-authed Function URL was the original plan for the
read route (one fewer public endpoint, no CORS at all) — see step 8 in
`BUILD_LOG.md` for the real AWS-side wall that sent it back to API Gateway.

## Status

Live: https://dqvgjpr92tnou.cloudfront.net

```
curl https://hicdw6b0v7.execute-api.us-east-1.amazonaws.com/dev/gallery
```

## Infra

CDK (TypeScript), one stack — see `docs/architecture.md` for why it isn't
three.

```
cd infra
npm install
npx cdk deploy
```

Outputs `SiteUrl`, `ApiUrl`, `GalleryTableName`.

Teardown: `npx cdk destroy`.
