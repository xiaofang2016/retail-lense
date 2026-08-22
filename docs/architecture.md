# Architecture

```
Users → (optional CloudFront) → ALB → EC2
  EC2 runs: Streamlit (frontend) + FastAPI (backend) + analysis workers
  EC2 → DynamoDB (Users, LoginHistory, PasswordReset, Otps, Analyses)
  EC2 → S3 (public / uploads / results)
  EC2 → SQS → EC2 workers
  EC2 → SNS (OTP, job complete)
  EC2 → Secrets Manager (JWT, OpenAI)
```

Compute is EC2 only. Database is DynamoDB only. Secrets Manager holds secrets (not SSM).
No user groups: each account is a standalone user.
