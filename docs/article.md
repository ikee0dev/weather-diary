# Weekend Creative Agent Challenge: Weather Diary

Tags: #agents

Every six hours, whether anyone is watching or not, the sky over Lagos gets five words written about it, a picture painted from those five words, and a caption written underneath. Nobody presses anything.

## Vision & What the App Does

This is a diary a place keeps about itself. An EventBridge schedule wakes a Lambda. The Lambda asks Open-Meteo what's actually happening over Lagos right now: temperature, wind, cloud cover, rain, day or night. A small vocabulary layer boils that down to five words. A picture gets painted from those five words. Gemini writes one first-person line about the same moment. The whole entry goes into a gallery that only grows. Visit the page and you aren't triggering anything. You're reading something that already happened without you there.

The picture is the part worth sitting with, because it isn't a generated image standing in for the data. It is the data, drawn. A hundred percent cloud cover doesn't get described to anything. It directly sets how many cloud shapes appear and how dense they look. Real wind direction sets the angle of the wind streaks. Real rain, when there is any, is the only reason rain appears on the page at all. A sun or a moon sits where the real local hour says it should, and dims by exactly as much as the real cloud cover dims it. Every stroke in that picture traces back to something Open-Meteo actually reported a few seconds before.

## How You Built It

The plan going in was to let Amazon Bedrock's Nova Canvas paint the sky. That never happened. The first real call came back throttled, too many requests. A second call, to a completely different model, five words of prompt, nothing to do with images, came back throttled too, this time with the message too many tokens per day. That second message is word for word identical to something already sitting in a sibling project's own build history, from a different app hitting this same account limit months earlier. Which means the fix, both times, is the same fix: file an AWS support case, and Basic support can't do that. Not something a weekend was going to solve, and I only knew that in fifteen minutes instead of a wasted afternoon because the first time it happened, someone bothered to write it down honestly.

So the picture gets drawn by code, not a model. Every app in this little series already leans on the same trick, turning real numbers into a small honest vocabulary before anything creative happens to them. This one just carries that a step further and skips the model at the very end, letting the vocabulary drive an SVG generator by itself. A bit of seeded randomness keeps three near identical cloudy nights from looking like the same picture copied three times, without breaking reproducibility. Feed it the same real minute twice and it paints the same way both times. Gemini is still doing real work here. It just moved jobs, from painting to writing.

Two smaller decisions came later, once something already worked. First, the app had started life as a copy of this series' other two CDK layouts, three stacks split into data, api, and hosting, and that was never the right size for one table, one writer, one reader, and one static page. So it got folded into a single stack. Second, less successful, I tried dropping API Gateway too, routing the one read endpoint through an IAM-authed Lambda Function URL sitting behind CloudFront's Origin Access Control, so there would be no separate public API domain at all. Every setting matched AWS's own documentation. The resource policy, the signing config, the origin domain. And CloudFront kept returning a flat access denied on every single request, survived a cache invalidation, survived a full redeploy, while CloudWatch logs showed the Lambda succeeding every time underneath it. That's a real seam between two AWS features not lining up, not a bug in this app, and rather than spend the rest of the weekend guessing at it, the read route went back to a plain API Gateway REST API, the same block already trusted twice elsewhere in this series.

## AWS Services Used / Architecture Overview

One CDK stack. AWS Lambda runs both the write path (weather, painting, captioning) and the read path (the gallery). Amazon EventBridge is the actual author here, a six-hour rate rule, on purpose not matched to either sibling project's own rhythm, so all three keep their own pace. Amazon DynamoDB holds the gallery with no TTL, because the growth is the point, and each picture sits inline as an SVG string rather than as a file in some bucket. Amazon API Gateway fronts the one read route. Secrets Manager holds the Gemini key. S3 and CloudFront serve the static frontend. Open-Meteo supplies the weather itself, no key, no cost, no limit hit all weekend. The full diagram lives in `docs/architecture.md` in the repo.

## What You Learned

The best moment of the whole build wasn't a feature landing clean. It was a wall landing familiar, recognizing this account's Bedrock throttle inside minutes because a different app, weeks earlier, had already written down exactly what it looks like. That alone is worth keeping an honest build log for. Not for anyone reading it later, just for the next project. The other thing I learned is about where a model actually needs to sit in something creative. The picture in this app is entirely deterministic code and it still doesn't feel mechanical, because the five words steering it are real. The one line Gemini writes under each picture does more to make three nearly identical cloudy nights feel like three separate entries than a fully generated image would have. Its job here was never to draw. It was to notice.

## Link to App or Repo

- Live app: https://dqvgjpr92tnou.cloudfront.net
- Source: https://github.com/ikee0dev/weather-diary
