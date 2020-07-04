import * as cdk from "@aws-cdk/core";
import * as ecrAsset from "@aws-cdk/aws-ecr-assets";
import * as ecs from "@aws-cdk/aws-ecs";
import * as ecsPattern from "@aws-cdk/aws-ecs-patterns";
import * as s3 from "@aws-cdk/aws-s3";
import * as ec2 from "@aws-cdk/aws-ec2";
import * as rds from "@aws-cdk/aws-rds";
import * as iam from "@aws-cdk/aws-iam";
import * as elasticache from "@aws-cdk/aws-elasticache";
import * as cloudfront from "@aws-cdk/aws-cloudfront";
import * as route53 from "@aws-cdk/aws-route53";
import * as targets from "@aws-cdk/aws-route53-targets";
import * as acm from "@aws-cdk/aws-certificatemanager";
import * as elb from "@aws-cdk/aws-elasticloadbalancingv2";
import * as secretsmanager from "@aws-cdk/aws-secretsmanager";

export class ThroatStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const base = this.node.tryGetContext("baseDns") ?? "phucks.co";
    const subname = this.node.tryGetContext("subname") ?? ""; // Such as www...
    const databaseName: string =
      this.node.tryGetContext("databaseName") ?? "phucks";
    const databaseUsername: string =
      this.node.tryGetContext("databaseUsername") ?? "phucks";

    // Set up S3 bucket
    const bucket = new s3.Bucket(this, "images", {
      encryption: s3.BucketEncryption.KMS,
      accessControl: s3.BucketAccessControl.PRIVATE,
    });

    // Set up VPC
    const vpc = new ec2.Vpc(this, "TheVPC", {
      enableDnsHostnames: false,
    });

    // Add redis
    const redis = new elasticache.CfnCacheCluster(this, "redis-cluster", {
      engine: "redis",
      cacheNodeType: "cache.t3.micro",
      numCacheNodes: 1,
      cacheSubnetGroupName: new elasticache.CfnSubnetGroup(
        this,
        "redis-subnet-group",
        {
          subnetIds: vpc.privateSubnets.map((s) => s.subnetId),
          description: "VPC Private Subnets",
        }
      ).cacheSubnetGroupName,
      vpcSecurityGroupIds: [vpc.vpcDefaultSecurityGroup], // Even money this doesn't work.
    });

    // Set up RDS
    const database = new rds.DatabaseInstance(this, "db", {
      engine: rds.DatabaseInstanceEngine.POSTGRES,
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.BURSTABLE3,
        ec2.InstanceSize.SMALL
      ), // TODO use nano for non "main" builds. Also, right size this.
      masterUsername: databaseUsername,
      vpc,
      storageEncrypted: true,
      multiAz: false,
      databaseName: databaseName,
      storageType: rds.StorageType.GP2,
      // TODO monitor performance and log things to cloudwatch
    });

    // Set up ECR Asset (Docker container)
    const asset = new ecrAsset.DockerImageAsset(this, "throat-asset", {
      directory: "../",
    });

    const role = new iam.Role(this, "throat-role", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });

    bucket.grantReadWrite(role);

    const cluster = new ecs.Cluster(this, "throat-cluster", { vpc });

    const zone = route53.HostedZone.fromLookup(this, "primary-zone", {
      domainName: base,
    });

    const cfnDomainName = `uploads.${subname}.${base}`;

    const certArn = new acm.DnsValidatedCertificate(this, "cfn-dist", {
      domainName: cfnDomainName,
      hostedZone: zone,
    }).certificateArn;

    const oai = new cloudfront.OriginAccessIdentity(this, "oai", {
      comment: `Uploads OAI for ${cfnDomainName}`,
    });

    // Create domain name & CloudFront distribution
    const cfdistro = new cloudfront.CloudFrontWebDistribution(
      this,
      "uploads-distribution",
      {
        aliasConfiguration: {
          acmCertRef: certArn,
          names: [cfnDomainName],
          sslMethod: cloudfront.SSLMethod.SNI,
          securityPolicy: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2018,
        },
        originConfigs: [
          {
            s3OriginSource: {
              s3BucketSource: bucket,
              originAccessIdentity: oai,
            },
            behaviors: [
              {
                allowedMethods: cloudfront.CloudFrontAllowedMethods.GET_HEAD,
                compress: true,
                isDefaultBehavior: true,
              },
            ],
          },
        ],
      }
    );

    new route53.ARecord(this, "cfn-ARecord", {
      zone,
      recordName: cfnDomainName,
      target: route53.RecordTarget.fromAlias(
        new targets.CloudFrontTarget(cfdistro)
      ),
    });
    new route53.AaaaRecord(this, "cfn-AaaaRecord", {
      zone,
      recordName: cfnDomainName,
      target: route53.RecordTarget.fromAlias(
        new targets.CloudFrontTarget(cfdistro)
      ),
    });

    const cookieSecret = new secretsmanager.Secret(this, "cookie-secret");

    const ecsStack = new ecsPattern.ApplicationLoadBalancedFargateService(
      this,
      "ecs",
      {
        cluster,
        domainZone: zone,
        domainName: `${subname}.${base}`,
        protocol: elb.ApplicationProtocol.HTTPS,
        taskImageOptions: {
          taskRole: role,
          image: ecs.ContainerImage.fromDockerImageAsset(asset),
          family: ec2.InstanceClass.BURSTABLE3,
          environment: {
            app_redis_url: `redis://${redis.attrRedisEndpointAddress}:${redis.attrRedisEndpointPort}`,
            app_debug: `false`,
            app_testing: `false`,
            cach_type: "redis",
            cach_redis_url: `redis://${redis.attrRedisEndpointAddress}:${redis.attrRedisEndpointPort}`,
            database_engine: "PostgresqlDatabase",
            database_host: database.instanceEndpoint.hostname,
            database_port: database.instanceEndpoint.port.toString(),
            database_name: databaseName,
            database_user: databaseUsername,
            storage_thumbnails_path: `s3://${bucket.bucketName}/thumbs`,
            storage_thumbnails_url: `https://${cfnDomainName}/thumbs`,
            storage_uploads_path: `s3://${bucket.bucketName}/upload`,
            storage_uploads_url: `https://${cfnDomainName}/upload`,
          },
          secrets: {
            app_secret_key: ecs.Secret.fromSecretsManager(cookieSecret),
            database_password: ecs.Secret.fromSecretsManager(database.secret!),
          },
          containerPort: 5000,
        },
        publicLoadBalancer: true,
      }
    );
  }
}
