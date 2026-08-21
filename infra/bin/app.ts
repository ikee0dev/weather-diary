#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { WeatherDiaryStack } from '../lib/weather-diary-stack';

const app = new cdk.App();

// Stage drives naming and prod-vs-dev behaviour. Override: cdk deploy -c stage=prod
const stage = app.node.tryGetContext('stage') || 'dev';

const env: cdk.Environment = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};

// One stack, on purpose - see weather-diary-stack.ts for why.
new WeatherDiaryStack(app, `wd-${stage}`, { env, stage });

cdk.Tags.of(app).add('project', 'weather-diary');
cdk.Tags.of(app).add('stage', stage);
