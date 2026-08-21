#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { DataStack } from '../lib/data-stack';
import { ApiStack } from '../lib/api-stack';
import { HostingStack } from '../lib/hosting-stack';

const app = new cdk.App();

// Stage drives naming and prod-vs-dev behaviour. Override: cdk deploy --all -c stage=prod
const stage = app.node.tryGetContext('stage') || 'dev';

const env: cdk.Environment = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};

const prefix = `wd-${stage}`;

// Storage layer - one DynamoDB table, the growing gallery.
const data = new DataStack(app, `${prefix}-data`, { env, stage });

// Compute + API - the unattended diary Lambda (EventBridge, every 6h) and
// the read-only gallery route.
const api = new ApiStack(app, `${prefix}-api`, { env, stage, gallery: data.gallery });

// Static hosting - S3 + CloudFront for the frontend, fed the API base URL.
new HostingStack(app, `${prefix}-hosting`, { env, stage, apiUrl: api.api.url });

cdk.Tags.of(app).add('project', 'weather-diary');
cdk.Tags.of(app).add('stage', stage);
