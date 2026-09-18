# Architecture

```
Users → (optional CloudFront) → ALB
  Frontend EC2: Streamlit only. No instance role, no AWS credentials.
  Backend EC2: FastAPI + analysis workers, instance role retaillen-backend-runtime
  Auth: Streamlit → one Lambda Function URL → /auth/signin or /auth/register
    Lambda → DynamoDB (Users + LoginHistory PutItem)
    Lambda → Secrets Manager (JWT)
  FastAPI GET /auth/login-history reads the same LoginHistory table
  Backend EC2 → DynamoDB (Users, LoginHistory, PasswordReset, Otps, Analyses)
  Backend EC2 → S3 (public / uploads / results)
  Backend EC2 → SQS → backend workers
  Backend EC2 → SNS (OTP, job complete)
  Backend EC2 → Secrets Manager (JWT, OpenAI)
```

Compute is EC2 plus a sign-in Lambda. Database is DynamoDB only. Secrets Manager holds secrets (not SSM).
No user groups: each account is a standalone user.
The Lambda uses its execution role (not IAM user `mike` / `AWS_PROFILE`).
