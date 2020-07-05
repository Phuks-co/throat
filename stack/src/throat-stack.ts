import * as acm from "@aws-cdk/aws-certificatemanager";
import * as cdk from "@aws-cdk/core";
import * as cloudfront from "@aws-cdk/aws-cloudfront";
import * as ec2 from "@aws-cdk/aws-ec2";
import * as ecs from "@aws-cdk/aws-ecs";
import * as ecsPattern from "@aws-cdk/aws-ecs-patterns";
import * as elasticache from "@aws-cdk/aws-elasticache";
import * as elb from "@aws-cdk/aws-elasticloadbalancingv2";
import * as iam from "@aws-cdk/aws-iam";
import * as rds from "@aws-cdk/aws-rds";
import * as route53 from "@aws-cdk/aws-route53";
import * as s3 from "@aws-cdk/aws-s3";
import * as secretsmanager from "@aws-cdk/aws-secretsmanager";
import * as targets from "@aws-cdk/aws-route53-targets";

export class ThroatStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const base = this.node.tryGetContext("baseDns") ?? "phuks.co";
    const subname = this.node.tryGetContext("subname") ?? ""; // Such as www...
    const databaseName: string =
      this.node.tryGetContext("databaseName") ?? "phuks";
    const databaseUsername: string =
      this.node.tryGetContext("databaseUsername") ?? "phuks";

    // Set up S3 bucket
    const bucket = new s3.Bucket(this, "images", {
      encryption: s3.BucketEncryption.KMS,
      accessControl: s3.BucketAccessControl.PRIVATE,
    });

    // Set up VPC
    const vpc = new ec2.Vpc(this, "TheVPC", {
      enableDnsHostnames: false,
    });

    const sg1 = new ec2.SecurityGroup(this, "sg1", {
      vpc,
      allowAllOutbound: true,
    });

    sg1.connections.allowFrom(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.allTcp()
    );
    const securityGroups = [
      ec2.SecurityGroup.fromSecurityGroupId(
        this,
        "default-vpc",
        vpc.vpcDefaultSecurityGroup
      ),
      sg1,
    ];

    const bastion = new ec2.BastionHostLinux(this, "bastion-host", {
      vpc,
    });

    const subnetGroup = new elasticache.CfnSubnetGroup(
      this,
      "redis-subnet-group",
      {
        cacheSubnetGroupName: "redissubnetgroup",
        subnetIds: vpc.privateSubnets.map((s) => s.subnetId),
        description: "VPC Private Subnets",
      }
    );

    // Add redis
    const redis = new elasticache.CfnCacheCluster(this, "redis-cluster", {
      engine: "redis",
      cacheNodeType: "cache.t3.micro",
      numCacheNodes: 1,
      cacheSubnetGroupName: subnetGroup.cacheSubnetGroupName,
      vpcSecurityGroupIds: securityGroups.map((sg) => sg.securityGroupId), // Even money this doesn't work.
    });

    redis.addDependsOn(subnetGroup);

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
      // securityGroups,
      // TODO monitor performance and log things to cloudwatch
    });

    bastion.connections.allowTo(database, ec2.Port.tcp(5432));
    database.connections.allowFrom(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.tcp(5432)
    );

    const role = new iam.Role(this, "throat-role", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });

    bucket.grantReadWrite(role);

    const cluster = new ecs.Cluster(this, "throat-cluster", { vpc });

    const zone = route53.HostedZone.fromLookup(this, "primary-zone", {
      domainName: base,
    });

    const cfnDomainName = `uploads.${subname}.${base}`;

    const certArn = new acm.DnsValidatedCertificate(this, "cft-dist-cert", {
      domainName: cfnDomainName,
      hostedZone: zone,
      region: "us-east-1",
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

    const environment = {
      APP_REDIS_URL: `redis://${redis.attrRedisEndpointAddress}:${redis.attrRedisEndpointPort}`,
      CACHE_TYPE: "redis",
      CACHE_REDIS_URL: `redis://${redis.attrRedisEndpointAddress}:${redis.attrRedisEndpointPort}`,
      DATABASE_ENGINE: "PostgresqlDatabase",
      STORAGE_THUMBNAILS_PATH: `s3://${bucket.bucketName}/thumbs`,
      STORAGE_THUMBNAILS_URL: `https://${cfnDomainName}/thumbs`,
      STORAGE_UPLOADS_PATH: `s3://${bucket.bucketName}/upload`,
      STORAGE_UPLOADS_URL: `https://${cfnDomainName}/upload`,
    };
    const secrets = {
      APP_SECRET_KEY: ecs.Secret.fromSecretsManager(cookieSecret),
      DATABASE_SECRET: ecs.Secret.fromSecretsManager(database.secret!),
    };

    const image = ecs.ContainerImage.fromAsset("../");
    const migration = new ecs.ContainerDefinition(this, "migration-container", {
      image,
      taskDefinition: new ecs.FargateTaskDefinition(this, "migration-task", {
        taskRole: role,
      }),
      environment,
      secrets,
      command: ["./scripts/migrate.py"],
    });

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
          image,
          family: ec2.InstanceClass.BURSTABLE3,
          environment,
          secrets,
          containerPort: 5000,
        },
        publicLoadBalancer: true,
      }
    );

    ecsStack.loadBalancer
      .addListener("http_https", {
        port: 80,
        protocol: elb.ApplicationProtocol.HTTP,
      })
      .addRedirectResponse("redirect", {
        port: "443",
        protocol: elb.ApplicationProtocol.HTTPS,
        statusCode: "HTTP_301",
      });

    ecsStack.node.addDependency(redis);
  }
}
