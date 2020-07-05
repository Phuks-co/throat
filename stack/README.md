# Throat Stack

This describes a containerized AWS stack for a throat instance. This stack is not free! It shouldn't be horribly expensive, but until I've run it under load I can't know what the cost will be.

## How to Use

You will need [cdk](https://docs.aws.amazon.com/cdk/latest/guide/home.html) [installed](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html#getting_started_install) in order to do a deployment.

You will also need an [AWS account](https://aws.amazon.com/), and you will probably want the [aws-cli](https://aws.amazon.com/cli/) installed. From there you'll need to set up a [profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html)

From there you will need to [bootstrap](https://docs.aws.amazon.com/cdk/latest/guide/tools.html) your AWS environment.

In order to use this you will also need your domain name in [Route53](https://aws.amazon.com/route53/) which can be done with just a hosted zone, and using Route53 as your name server.

Once that is set up you can then run the following command (if for instance you were trying to set up www.phuks.co)

```
cdk deploy \
   -c baseDns="phuks.co" 
   -c subname="www" 
   -c databaseName="phuks" 
   -c databaseUsername="phuks" 
   --profile "phuks"
```

## What it will do

The above command will do the following

* Set up an encrypted [S3](https://aws.amazon.com/s3/) bucket for use in upload and thumbnail handling
* Creates a [CloudFront Distribution](https://aws.amazon.com/cloudfront/) to handle serving uploads
* Creates a DNS entry for `uploads.www.phuks.co` and an associated SSL certificate
* Set up a [VPC](https://aws.amazon.com/vpc/) with no public endpoints allowed inside of it.
* Create a bastion host which can be accessed with [Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html) in order to "see" inside the VPC.
* Creates a [Elasticache Redis Cluster](https://aws.amazon.com/elasticache/) to handle the caching required by throat.
* Creates a [Postgres RDS Instance](https://aws.amazon.com/rds/postgresql/) that is encrypted.
* Creates a [ECS Fargate](https://aws.amazon.com/ecs/) Task of the throat server
* Creates a [ECS Fargate](https://aws.amazon.com/ecs/) Task of the throat migration
* Creates a [ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html) that will dynamically route to throat servers spun up by Fargate.
* Creates a DNS entry for `www.phuks.co` and an SSL certificate, attached to the ALB.

As a note, at the moment the amount of monitoring that is done is limited, we don't capture most of the metrics that we could be capturing, this is a TODO.

