# Team IAM roles

Create one IAM user/role per member with least privilege. Members may hold multiple roles.

| Course role | Member (proposal) | AWS access needed |
| --- | --- | --- |
| Infrastructure & Deployment | Mike Xiao | EC2, ALB, EICE, CloudWatch billing, sign-in Lambda CLI deploy (see `signin-lambda-deployer.json`) |
| Authentication & Security | Farhan Hridoy | Secrets Manager, SNS, IAM policy review (attach the deployer policy to `mike`) |
| Data & ML Pipeline | Tahreem Tahir | S3, DynamoDB, SQS |
| LLM & reference analysis | Arya Dhuri | Secrets Manager (OpenAI), S3 reports |
| Frontend & Monitoring | Ei Thae | CloudWatch dashboards and alarms |

IAM user `mike` cannot create Lambda functions until Farhan attaches `signin-lambda-deployer.json`. The Lambda uses the execution role `retaillen-signin-lambda` (`signin-lambda-execution.json`), not `AWS_PROFILE=mike`. Deploy with the AWS CLI or console — no CloudFormation, no API Gateway.

Both `retaillen-signin-lambda` and the backend EC2 role need `secretsmanager:GetSecretValue` on `retaillen/jwt`. Production processes set only `JWT_SECRET_NAME=retaillen/jwt`; the secret value must not be stored in Lambda or EC2 environment variables. Backend also reads `retaillen/SMTP_USER` and `retaillen/SMTP_PASSWORD` when `APP_ENV=aws`, SMTP is enabled, and those `.env` values are empty.

Frontend EC2 reads `AUTH_API_URL`, `REDIS_URL`, `REDIS_PASSWORD`, and `SESSION_COOKIE_PASSWORD` from Secrets Manager as `retaillen/<ENV_VAR>` when `APP_ENV=aws` and those `.env` values are empty. Locally put real values in `.env` instead.

The sign-in Lambda also needs `retaillen-otps` plus `sns:Publish` so a 2FA login can send the SMS (see `signin-lambda-execution.json`). Set `SNS_SMS_ENABLED=true` on Lambda and backend EC2 when using real SNS.

EC2 instance role (trust document: `ec2-runtime-trust.json`):

| Role | Policy | Why |
| --- | --- | --- |
| `retaillen-backend-runtime` | `retaillen-backend-runtime-policy.json` | FastAPI + clustering worker: DynamoDB, S3, SQS, SNS, Secrets Manager. Live role name is `retail-ec2role`. |
| `retaillen-frontend-runtime` | `frontend-runtime.json` | Streamlit: `secretsmanager:GetSecretValue` on `retaillen/AUTH_API_URL`, `retaillen/REDIS_URL`, `retaillen/REDIS_PASSWORD`, `retaillen/SESSION_COOKIE_PASSWORD`, plus CloudWatch logs on `/retaillen/frontend`. Live role name is `retail-frontend-runtime-role`. No CloudWatch agent policy and no `AmazonSSMManagedInstanceCore`. |

Do not give frontend DynamoDB/S3/SQS. Do not put `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, or `AWS_PROFILE` on frontend EC2. Omit `AWS_PROFILE` on backend instances (do not set it to an empty string) so boto3 uses instance role `retaillen-backend-runtime`. Containers need IMDSv2 hop limit ≥ 2 to reach the instance role.

GitHub Actions deploy user `github-eice` (`github-eice.json`): attach this to `github-eice`. `aws ec2-instance-connect ssh` always calls `ec2:DescribeInstances` (even with `--instance-id` and `endpointId`), then `ec2:DescribeInstanceConnectEndpoints` unless `dnsName` is also passed, then `SendSSHPublicKey` and `OpenTunnel`. Laptop user `mike` already has Describe; CI keys do not.

Do not issue long-lived access keys into the repo. Backend EC2 uses an instance profile. Do not use SSM for access or parameters.
