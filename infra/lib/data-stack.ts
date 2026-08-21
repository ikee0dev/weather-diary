import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';

interface DataStackProps extends cdk.StackProps {
  stage: string;
}

/**
 * Storage layer - one DynamoDB table. Each entry's SVG art is stored
 * inline as a string attribute rather than as a separate S3 object: the
 * pictures are small procedural markup (a few KB), so a second storage
 * layer (bucket, OAC, presigning) would be complexity this app does not
 * need. pk=LATEST is the fast single read; pk=ENTRY/sk=timestamp is the
 * growing gallery. No TTL - the accumulating gallery is the point of the
 * demo, not a side effect to clean up.
 */
export class DataStack extends cdk.Stack {
  public readonly gallery: dynamodb.Table;

  constructor(scope: Construct, id: string, props: DataStackProps) {
    super(scope, id, props);
    const isProd = props.stage === 'prod';

    this.gallery = new dynamodb.Table(this, 'Gallery', {
      tableName: `wd-gallery-${props.stage}`,
      partitionKey: { name: 'pk', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'sk', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: isProd ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    new cdk.CfnOutput(this, 'GalleryTableName', { value: this.gallery.tableName });
  }
}
