# Weekend Creative Agent Challenge: Weather Diary

Tags: #agents

Every six hours, whether or not anyone is watching, the sky over Lagos gets
five words written about it, a picture painted from those five words, and
a caption written under the picture. Nobody presses anything.

## Vision & What the App Does

This is a diary that a place keeps about itself. An EventBridge schedule
wakes a Lambda; the Lambda asks Open-Meteo what's really happening over
Lagos right now (temperature, wind, cloud cover, rain, day or night); a
small vocabulary layer boils that down to five words; a picture gets
painted from those five words; Gemini writes one first-person line about
the same moment; the whole entry gets filed into a gallery that only ever
grows. Visit the page and you're not triggering anything — you're reading
something that already happened without you.

The picture is the part worth dwelling on, because it isn't a generated
image standing in for the data — it's the data, drawn. 100% cloud cover
doesn't get described to anything; it directly sets how many cloud shapes
appear on the canvas and how dense they look. Real wind direction sets the
angle of the wind streaks. Real precipitation, when there is any, is what
puts rain on the page at all. A sun or moon sits where the real local hour
says it should, and dims exactly as much as the real cloud cover dims it.
Every stroke on that SVG traces back to a number Open-Meteo actually
reported a few seconds earlier.

## How You Built It

Amazon Bedrock's Nova Canvas was supposed to paint the sky. It never got
the chance: the first real call came back `ThrottlingException: Too many
requests`, and a second call to a completely different model — `nova-micro`,
five words of prompt, nothing to do with images — came back
`ThrottlingException: Too many tokens per day`. That second message is
word-for-word identical to an incident already logged in a sibling
project's history (`debugging-saga`'s showcase story about `standup-brief`),
which means this account has hit the same real daily allowance wall twice
now, on two different apps, and the fix both times is the same: file an
AWS Support case, which Basic support can't do. Not fixable this weekend,
confirmed inside fifteen minutes instead of a wasted afternoon, because the
first incident was written down honestly instead of quietly worked around.

So the picture is drawn by code, not a model. Every app in this series
already leans on the same trick — translate real numbers into a small
honest vocabulary before anything creative happens — and this one just
pushes that trick one step further: skip the model at the end entirely and
let the vocabulary drive an SVG generator directly. A `random.Random`
seeded on the real observation timestamp keeps three near-identical cloudy
nights from looking like the same picture copy-pasted three times, without
making the output non-reproducible — the same real minute always paints
the same way. Gemini is still doing real work; it just moved from painting
to writing.

Two more decisions got made after the fact, once a working version existed.
First: the app started life as a straight copy of this series' other two
CDK layouts — three stacks, data/api/hosting — and that was never actually
the right size for one table, one writer, one reader, and one static site.
Collapsed it to a single stack. Second, and less successful: tried to drop
API Gateway too, routing the one read endpoint through an IAM-authed
Lambda Function URL sitting behind CloudFront's Origin Access Control, so
there would be no separately-public API domain at all. Every setting on
both sides matched AWS's own documentation exactly — the resource policy,
the OAC signing config, the origin domain — and CloudFront still returned
a flat `AccessDeniedException` on every request, survived a cache
invalidation, survived a full redeploy, while CloudWatch logs showed the
Lambda itself succeeding every single time. That's a real gap between two
AWS features, not a bug in this app, and rather than keep guessing at it
for a weekend, the read route went back to a plain API Gateway REST API —
the same block already trusted twice over elsewhere in this series.

## AWS Services Used / Architecture Overview

One CDK stack. AWS Lambda runs both the write path (weather, painting,
captioning) and the read path (the gallery). Amazon EventBridge is the
actual author of the app — a 6-hour rate rule, deliberately not matched to
either sibling project's cadence, so the three entries in this series each
keep their own rhythm. Amazon DynamoDB holds the gallery with no TTL,
because growth is the point, and each picture lives inline as an SVG
string attribute rather than as a file in a bucket somewhere. Amazon API
Gateway fronts the one read route. AWS Secrets Manager holds the Gemini
key. Amazon S3 + CloudFront serve the static frontend. Open-Meteo supplies
the weather itself, no key, no cost, no rate limit hit all weekend. See
`docs/architecture.md` in the repo for the full sequence diagram.

## What You Learned

The build's best moment wasn't a feature landing clean, it was a wall
landing familiar — recognizing this account's Bedrock throttle inside
minutes because a different app, weeks earlier, had already written down
exactly what it looks like. That's the whole case for keeping an honest
build log: not for an audience, for the next project. The second lesson
is about where creativity actually needs a model in the loop. The picture
in this app is entirely deterministic code, and it still doesn't feel
mechanical, because the five words steering it are real. The one line
Gemini writes under each picture does more to make three nearly identical
cloudy nights feel like three separate diary entries than a fully
generated image would have — the model's job here was never to draw, it
was to notice.

## Link to App or Repo

- Live app: https://dqvgjpr92tnou.cloudfront.net
- Source: https://github.com/ikee0dev/weather-diary
