import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as path from 'path';

// Created out of band (never in CloudFormation, so a stack delete cannot
// take a credential with it): weather-diary/gemini { "api_key": ... }
export const GEMINI_SECRET_NAME = 'weather-diary/gemini';

interface ApiStackProps extends cdk.StackProps {
  stage: string;
  gallery: dynamodb.Table;
}

/**
 * Compute + API. diary.py is the whole point of the app: EventBridge calls
 * it on its own, no human, no API Gateway involved, so it can take the
 * full weather-fetch + art + caption chain's time without racing a 29s
 * wall. GET /gallery is the only route - read-only, public, never spends
 * model quota no matter how hard anyone refreshes.
 */
export class ApiStack extends cdk.Stack {
  public readonly api: apigw.RestApi;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);
    const { gallery } = props;
    const lambdasPath = path.join(__dirname, '..', 'lambdas');

    const geminiSecret = secretsmanager.Secret.fromSecretNameV2(
      this, 'GeminiSecret', GEMINI_SECRET_NAME);

    const diaryFn = new lambda.Function(this, 'DiaryFn', {
      functionName: `wd-diary-${props.stage}`,
      description: 'Reads real weather, paints it, captions it, unattended.',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'diary.handler',
      code: lambda.Code.fromAsset(lambdasPath, { exclude: ['__pycache__'] }),
      timeout: cdk.Duration.seconds(60),
      memorySize: 256,
      environment: {
        GALLERY_TABLE: gallery.tableName,
        GEMINI_SECRET_NAME,
        MODEL_ID: this.node.tryGetContext('model') || 'gemini-flash-latest',
        MODEL_FALLBACKS: this.node.tryGetContext('modelFallbacks') || 'gemini-3.5-flash-lite',
        WD_LAT: this.node.tryGetContext('lat') || '6.5244',
        WD_LON: this.node.tryGetContext('lon') || '3.3792',
        WD_TZ: this.node.tryGetContext('tz') || 'Africa/Lagos',
        WD_CITY: this.node.tryGetContext('city') || 'Lagos',
      },
    });
    gallery.grantWriteData(diaryFn);
    geminiSecret.grantRead(diaryFn);

    // 4 times a day: a real diary cadence would be once daily, but this
    // is more frequent on purpose so the gallery visibly grows inside a
    // 3-day judging window - said plainly in the article, not hidden.
    new events.Rule(this, 'DiarySchedule', {
      ruleName: `wd-diary-${props.stage}`,
      schedule: events.Schedule.rate(cdk.Duration.hours(6)),
      targets: [new targets.LambdaFunction(diaryFn)],
    });

    const galleryFn = new lambda.Function(this, 'GalleryFn', {
      functionName: `wd-gallery-${props.stage}`,
      description: 'Read-only gallery of every real entry so far.',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'get_gallery.handler',
      code: lambda.Code.fromAsset(lambdasPath, { exclude: ['__pycache__'] }),
      timeout: cdk.Duration.seconds(10),
      memorySize: 256,
      environment: { GALLERY_TABLE: gallery.tableName },
    });
    gallery.grantReadData(galleryFn);

    this.api = new apigw.RestApi(this, 'Api', {
      restApiName: `wd-${props.stage}`,
      deployOptions: { stageName: props.stage },
      defaultCorsPreflightOptions: {
        allowOrigins: apigw.Cors.ALL_ORIGINS,
        allowMethods: ['GET', 'OPTIONS'],
        allowHeaders: ['Content-Type'],
      },
    });

    this.api.root.addResource('gallery').addMethod('GET', new apigw.LambdaIntegration(galleryFn));

    new cdk.CfnOutput(this, 'ApiUrl', { value: this.api.url });
  }
}
