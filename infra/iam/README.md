# Team IAM roles

Create one IAM user/role per member with least privilege. Members may hold multiple roles.

| Course role | Member (proposal) | AWS access needed |
| --- | --- | --- |
| Infrastructure & Deployment | Mike Xiao | EC2, ALB, CloudWatch billing, CloudFormation |
| Authentication & Security | Farhan Hridoy | Secrets Manager, SNS, IAM policy review |
| Data & ML Pipeline | Tahreem Tahir | S3, DynamoDB, SQS |
| LLM & reference analysis | Arya Dhuri | Secrets Manager (OpenAI), S3 reports |
| Frontend & Monitoring | Ei Thae | CloudWatch dashboards and alarms |

Do not issue long-lived access keys into the repo. EC2 uses an instance profile. Do not use SSM for access or parameters.
