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
* Create a [CloudFront Distribution](https://aws.amazon.com/cloudfront/) to handle serving uploads
* Create a DNS entry for `uploads.www.phuks.co` and an associated SSL certificate
* Set up a [VPC](https://aws.amazon.com/vpc/) with no public endpoints allowed inside of it.
* Create a bastion host which can be accessed with [Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html) in order to "see" inside the VPC.
* Create a [Elasticache Redis Cluster](https://aws.amazon.com/elasticache/) to handle the caching required by throat.
* Create a [Postgres RDS Instance](https://aws.amazon.com/rds/postgresql/) that is encrypted.
* Create a [ECS Fargate](https://aws.amazon.com/ecs/) Task of the throat server
* Create a [ECS Fargate](https://aws.amazon.com/ecs/) Task of the throat migration
* Create a [ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html) that will dynamically route to throat servers spun up by Fargate.
* Create a DNS entry for `www.phuks.co` and an SSL certificate, attached to the ALB.

As a note, at the moment the amount of monitoring that is done is limited, we don't capture most of the metrics that we could be capturing, this is a TODO.

## How do I?

Note, all example URLs are in US-West-2, if you are somewhere different you'll need to change your region.

### Execute a Migration

* Go to [Task Definitions](https://us-west-2.console.aws.amazon.com/ecs/home?region=us-west-2#/taskDefinitions/) and find the ThroatStackMigration{random numbers}, and then click in on it.
* Select the tasks, find the Actions dropdown, and select "Run Task"
* Select "Fargate" Makesure the cluster is "ThroatStack", number of tasks 1, that your Cluster VPC is correct, choose a subnet
* press "Run Task

OR do the following

* `aws ec2 describe-subnets` find a SubnetID associated with your "stack", you'll be able to tell because it will have a tag of `aws:cloudformation:stack-name`. - SUBNET
* `aws ecs list-cluster` find the cluster arn associated with your stack (It will have the stack name in the arn) - CLUSTER
* `aws ecs list-task-definitions` find the migration task (Has the word migration in it) - TASK
* ```aws ecs run-task \
--cluster "${CLUSTER}" \
--launch-type FARGATE \
--network-configuration="awsvpcConfiguration={subnets=[${SUBNET}]}" \
--task-definition="${TASK}"
```

### Add an Admin

* `aws ec2 describe-subnets` find a SubnetID associated with your "stack", you'll be able to tell because it will have a tag of `aws:cloudformation:stack-name`. - SUBNET
* `aws ecs list-cluster` find the cluster arn associated with your stack (It will have the stack name in the arn) - CLUSTER
* `aws ecs list-task-definitions` find the migration task (Has the word migration in it) - TASK
* ```aws ecs run-task \
--cluster "${CLUSTER}" \
--launch-type FARGATE \
--network-configuration="awsvpcConfiguration={subnets=[${SUBNET}]}" \
--task-definition="${TASK}"
--overrides='{"containerOverrides": [{"name": "migration-container", "command": ["./scripts/admins.py", "--add", "${username}"]}]}'
```

