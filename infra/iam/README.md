# Team IAM roles

Create one IAM user/role per member with least privilege. Members may hold multiple roles.

| Course role | Member (proposal) | AWS access needed |
| --- | --- | --- |
| Infrastructure & Deployment | Mike Xiao | EC2, ALB, CloudWatch billing, CloudFormation, sign-in Lambda CLI deploy (see `signin-lambda-deployer.json`) |
| Authentication & Security | Farhan Hridoy | Secrets Manager, SNS, IAM policy review (attach the deployer policy to `mike`) |
| Data & ML Pipeline | Tahreem Tahir | S3, DynamoDB, SQS |
| LLM & reference analysis | Arya Dhuri | Secrets Manager (OpenAI), S3 reports |
| Frontend & Monitoring | Ei Thae | CloudWatch dashboards and alarms |

IAM user `mike` cannot create Lambda functions until Farhan attaches `signin-lambda-deployer.json`. The Lambda uses the execution role `retaillen-signin-lambda` (`signin-lambda-execution.json`), not `AWS_PROFILE=mike`. Deploy with the AWS CLI or console — no CloudFormation, no API Gateway.

Both `retaillen-signin-lambda` and the backend EC2 role need `secretsmanager:GetSecretValue` on `retaillen/jwt`. Production processes set only `JWT_SECRET_NAME=retaillen/jwt`; the secret value must not be stored in Lambda or EC2 environment variables.

The sign-in Lambda also needs `retaillen-otps` plus `sns:Publish` so a 2FA login can send the SMS (see `signin-lambda-execution.json`). Set `SNS_SMS_ENABLED=true` on Lambda and backend EC2 when using real SNS.

EC2 instance role (trust document: `ec2-runtime-trust.json`):

| Role | Policy | Why |
| --- | --- | --- |
| `retaillen-backend-runtime` | `backend-runtime.json` | FastAPI + clustering worker: DynamoDB, S3, SQS, SNS, Secrets Manager. |

Frontend EC2 instances do not get an instance profile and must not receive `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, or `AWS_PROFILE`. Streamlit talks only to FastAPI, Redis, and S3 presigned URLs (signed by the backend). Leave `AWS_PROFILE` empty on the backend instances so boto3 uses the instance profile.

Do not issue long-lived access keys into the repo. Backend EC2 uses an instance profile. Do not use SSM for access or parameters.
