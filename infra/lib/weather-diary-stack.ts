import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as path from 'path';

// Created out of band (never in CloudFormation, so a stack delete cannot
// take a credential with it): weather-diary/gemini { "api_key": ... }
export const GEMINI_SECRET_NAME = 'weather-diary/gemini';

interface WeatherDiaryStackProps extends cdk.StackProps {
  stage: string;
}

/**
 * The whole app in one stack, on purpose - a deliberately different shape
 * from the other two entries in this series, which both split data/api/
 * hosting across three. This app has exactly one table, one scheduled
 * writer, one public reader and one static site; three stacks would only
 * add cross-stack exports for their own sake.
 *
 * A CloudFront-proxied, IAM-authed Lambda Function URL was the first
 * attempt at the read route, specifically to avoid API Gateway too, but
 * hit a genuine `AccessDeniedException` from CloudFront's Origin Access
 * Control against a Lambda Function URL origin that would not clear even
 * with a correct resource policy, a correct OAC config (sigv4/always/
 * lambda), and a cache invalidation - a real, currently-unresolved gap
 * between two AWS features rather than a bug in this app. Reverted to a
 * one-route API Gateway REST API instead: less exotic, but proven
 * reliable in the other two entries in this series.
 */
export class WeatherDiaryStack extends cdk.Stack {
  public readonly siteUrl: string;

  constructor(scope: Construct, id: string, props: WeatherDiaryStackProps) {
    super(scope, id, props);
    const isProd = props.stage === 'prod';
    const removal = isProd ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY;
    const lambdasPath = path.join(__dirname, '..', 'lambdas');

    // Gallery table. No TTL - the growing gallery is the whole demo.
    const gallery = new dynamodb.Table(this, 'Gallery', {
      tableName: `wd-gallery-${props.stage}`,
      partitionKey: { name: 'pk', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'sk', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: removal,
    });

    const geminiSecret = secretsmanager.Secret.fromSecretNameV2(
      this, 'GeminiSecret', GEMINI_SECRET_NAME);

    // The whole point of the app: EventBridge calls this on its own.
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

    // 4 times a day: a real diary cadence would be once daily, but this is
    // more frequent on purpose so the gallery visibly grows inside a 3-day
    // judging window - said plainly in the article, not hidden. Also
    // deliberately not the same interval as the other two entries in this
    // series (15 min, 3 hours) - three different rhythms to compare.
    new events.Rule(this, 'DiarySchedule', {
      ruleName: `wd-diary-${props.stage}`,
      schedule: events.Schedule.rate(cdk.Duration.hours(6)),
      targets: [new targets.LambdaFunction(diaryFn)],
    });

    // Read-only gallery. One route, so one Lambda behind API Gateway
    // rather than a resource tree built for growth this app doesn't need.
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

    const api = new apigw.RestApi(this, 'Api', {
      restApiName: `wd-${props.stage}`,
      deployOptions: { stageName: props.stage },
      defaultCorsPreflightOptions: {
        allowOrigins: apigw.Cors.ALL_ORIGINS,
        allowMethods: ['GET', 'OPTIONS'],
        allowHeaders: ['Content-Type'],
      },
    });
    api.root.addResource('gallery').addMethod('GET', new apigw.LambdaIntegration(galleryFn));

    // Static hosting - S3 + CloudFront, same shape as the other two
    // entries (there is no interesting way to reinvent static hosting).
    const siteBucket = new s3.Bucket(this, 'SiteBucket', {
      bucketName: `wd-web-${props.stage}-${this.account}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: removal,
      autoDeleteObjects: !isProd,
    });

    const dist = new cloudfront.Distribution(this, 'SiteDist', {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(siteBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: 'index.html',
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
    });

    new s3deploy.BucketDeployment(this, 'DeployWeb', {
      sources: [
        s3deploy.Source.asset(path.join(__dirname, '..', '..', 'web')),
        s3deploy.Source.data('config.js', `window.WD_API_BASE = ${JSON.stringify(api.url)};`),
      ],
      destinationBucket: siteBucket,
      distribution: dist,
      distributionPaths: ['/*'],
    });

    this.siteUrl = `https://${dist.distributionDomainName}`;
    new cdk.CfnOutput(this, 'SiteUrl', { value: this.siteUrl });
    new cdk.CfnOutput(this, 'ApiUrl', { value: api.url });
    new cdk.CfnOutput(this, 'GalleryTableName', { value: gallery.tableName });
  }
}
