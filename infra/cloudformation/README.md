# CloudFormation (documentation only)

`stack.yaml` describes the Retail Lense production layout (VPC, security groups, ALB, three EC2 hosts, EICE, IAM, DynamoDB, S3, SQS, SNS, sign-in Lambda Function URL).

**Do not deploy this stack into account `817817875692`.** Those resources already exist; they were created with the AWS CLI. Applying the template would try to create a second VPC, ALB, bucket, tables, and instances.

Application updates stay on GitHub Actions + EICE (`../scripts/deploy_ec2_*.sh`). This file is the Moodle IaC artefact: a readable equivalent of the CLI-built account.

Secrets Manager names (`retaillen/jwt`, `retaillen/openai`, Redis, SMTP, frontend session secrets) are **not** created here. IAM only grants `GetSecretValue` on those names. The ALB certificate is an IAM server certificate (ACM is out of scope); pass its ARN if you ever launched a copy in an empty account.

Validate locally if you want:

```bash
aws cloudformation validate-template \
  --template-body file://infra/cloudformation/stack.yaml
```
