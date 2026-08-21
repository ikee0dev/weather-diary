# Weekend Creative Agent Challenge: Weather Diary

Tags: #agents

A sky that paints itself a picture and writes itself a caption, every six
hours, whether or not anyone is watching.

## Vision & What the App Does

Weather Diary reads the real current weather over Lagos, Nigeria — no API
key required, Open-Meteo just answers — and turns that single moment into
one diary entry: a small painted sky and a one-line first-person caption,
as if the sky itself were keeping a journal. Nobody presses a button.
Every six hours, an EventBridge schedule wakes a Lambda, it reads whatever
is really happening outside right now, and by the time anyone visits the
page there's something new waiting, filed in with everything before it.
The gallery only ever grows.

The picture isn't decoration bolted onto a data feed — it's built directly
from the numbers. Cloud cover controls how many cloud puffs drift across
the frame and how dense they look. Wind speed and direction decide how
many wind streaks appear and which way they lean. Precipitation, when
there is any, draws real rain at an angle that matches the real wind. The
sun or moon sits at a position derived from the real local hour and
dims honestly behind heavy cloud rather than just vanishing. Every one of
those choices is deterministic, given the same real inputs — the picture
is a direct translation of the weather, not an approximation of it.

## How You Built It

The plan going in was to let Amazon Bedrock's Nova Canvas paint the sky.
The code for it was written and ready before I ever pointed it at the
model. The first real invocation came back `ThrottlingException: Too many
requests`. A 15-second retry got the same error. To find out whether that
was a Nova Canvas rate limit or something bigger, I invoked a second,
completely unrelated Bedrock model — `nova-micro`, five words of prompt —
and got `ThrottlingException: Too many tokens per day`, the exact same
message, word for word, that shows up in this account's own build history:
it's one of the four true showcase stories in a sibling project of mine,
`debugging-saga`, about a different app hitting this same account-level
daily allowance months ago. That earlier incident already established the
only real fix is an AWS Support case, and Basic support can't file one.
So this wasn't a fluke and it wasn't fixable this weekend.

I didn't fake the picture and I didn't quietly swap in a different
foundation model and call it a day. Every other app in this series already
runs on one core technique — a "descriptor pool" that maps real numbers
into a small honest vocabulary before anything creative happens to them —
so I applied that same technique one layer further and let *code* paint
the picture directly from the vocabulary, with no model in that step at
all. Cloud cover of 100% doesn't ask a model to imagine an overcast sky; it
directly sets how many cloud shapes get drawn and how opaque they are. A
`random.Random` seeded on the real observation timestamp adds shape
variety — three consecutive entries built from nearly identical real
conditions still look like different moments — without breaking
reproducibility: the same real minute always paints the same picture.
Gemini still does real work in the pipeline, writing the caption from the
same real numbers, because that part of the account has never been
throttled.

I proved the whole chain by invoking the deployed Lambda directly three
times in a row against real live conditions (25.6C, 100% cloud, calm wind,
no rain, nighttime) and got three different, specific captions back, never
generic ones — "a heavy, silent blanket resting over Lagos tonight," "a
heavy, unbroken ceiling of gray draped silently over the sleeping city" —
each one served back through the real API with its real picture intact,
and confirmed live in a browser: three distinct night skies, each with its
own drifting clouds, a moon dimmed almost to nothing under real 100% cloud
cover.

## AWS Services Used / Architecture Overview

CDK-TS, three stacks: AWS Lambda (weather fetch, art generation, caption,
and the read API), Amazon EventBridge (the 6-hour schedule that makes this
an agent rather than a button someone has to press), Amazon DynamoDB (the
gallery table — deliberately no TTL, because the growing gallery is the
whole demo, not a byproduct to clean up), Amazon API Gateway (one
read-only `GET /gallery`, so a visit never spends model quota), AWS
Secrets Manager (the Gemini key), and Amazon S3 + Amazon CloudFront for
the frontend. Open-Meteo supplies the real weather with no key and no
cost. Google Gemini writes the caption; Amazon Bedrock was the original
plan for the art and the account-level throttle above is the honest reason
it isn't in the final pipeline.

## What You Learned

The most useful thing that happened this weekend wasn't the feature that
worked on the first try, it was hitting a wall I recognized. This
account's Bedrock throttle had already been diagnosed once, in a
completely different project, months ago, and documented honestly instead
of hidden — and that documentation is exactly what let me spend fifteen
minutes confirming the same wall instead of a day debugging it fresh. That
alone is a good argument for writing these build logs at all. The second
lesson is about where "AI" actually needs to sit in a creative pipeline:
it doesn't have to be the part that draws the picture to be the part that
makes the picture feel alive. A caption and a title, written by a model
that actually looked at the real numbers, did more to make three nearly
identical cloudy nights feel like three different diary entries than a
generated image would have.

## Link to App or Repo

- Live app: https://d24q0uqc2v91xq.cloudfront.net
- Source: https://github.com/dayzer0-dev/weather-diary
