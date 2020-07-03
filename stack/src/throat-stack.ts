import * as cdk from "@aws-cdk/core";
import * as ecr from "@aws-cdk/aws-ecr";
import * as ecrAsset from "@aws-cdk/aws-ecr-assets";
import * as ecs from "@aws-cdk/aws-ecs";
import * as ecsPattern from "@aws-cdk/aws-ecs-patterns";
import * as s3 from "@aws-cdk/aws-s3";
import * as ec2 from "@aws-cdk/aws-ec2";
import * as rds from "@aws-cdk/aws-rds";
import * as iam from "@aws-cdk/aws-iam";
import * as elasticache from "@aws-cdk/aws-elasticache";

export class ThroatStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

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

    const databaseName: string =
      this.node.tryGetContext("databaseName") ?? "phucks";
    const databaseUsername: string =
      this.node.tryGetContext("databaseUsername") ?? "phucks";

    // Set up RDS
    const database = new rds.DatabaseInstance(this, "db", {
      engine: rds.DatabaseInstanceEngine.POSTGRES,
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.BURSTABLE3,
        ec2.InstanceSize.SMALL
      ), // TODO use nano for non "main" builds. Also, right size this.
      masterUsername: databaseUsername,
      vpc,
      multiAz: false,
      databaseName: databaseName,
      storageType: rds.StorageType.GP2,
      // TODO monitor performance and log things to cloudwatch
    });

    // Set up ECR Repo
    const repo = new ecr.Repository(this, "throat-ecr", {});

    // Set up ECR Asset (Docker container)
    const asset = new ecrAsset.DockerImageAsset(this, "throat-asset", {
      directory: "../docker",
      repositoryName: repo.repositoryName,
    });

    const role = new iam.Role(this, "throat-role", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });

    bucket.grantReadWrite(role);

    const cluster = new ecs.Cluster(this, "throat-cluster", { vpc });

    const ecsStack = new ecsPattern.ApplicationLoadBalancedFargateService(
      this,
      "ecs",
      {
        cluster,
        taskImageOptions: {
          taskRole: role,
          image: ecs.ContainerImage.fromDockerImageAsset(asset),
          family: ec2.InstanceClass.BURSTABLE3,
          environment: {
            databaseName,
            databaseUsername,
          },
          secrets:
            database.secret == null
              ? {}
              : { databasePassword: database.secret as any },
        },
        publicLoadBalancer: true,
      }
    );

    // Point ALB at S3 Bucket
    // both /thumbs/ and /upload/ Do we want the same bucket? or different buckets?
  }
}
