# Architecture

As deployed 25 September 2026. Backend is in a private subnet; IPv4 egress is instance NAT on frontend 1C (no NAT Gateway).

```mermaid
flowchart TB
  Browser --> DNS["www.retaillen.cloud"]
  DNS --> CF[CloudFront]
  CF -->|HTTPS| ALB["ALB :443<br/>us-east-1a / 1c"]

  subgraph AUTH["Auth — outside VPC"]
    LAM["Sign-in Lambda<br/>Function URL"]
    DDBU["DynamoDB<br/>users, OTPs, login history"]
    SNSOTP["SNS SMS OTP"]
    LAM --> DDBU
    LAM --> SNSOTP
  end

  subgraph VPC["VPC us-east-1"]
    ALB --> FEA["Frontend 1A<br/>Streamlit :8501<br/>public"]
    ALB --> FEC["Frontend 1C<br/>Streamlit :8501<br/>public + NAT"]

    subgraph PRIV["Private subnet 172.31.96.0/20 — us-east-1d — no public IP"]
      API["FastAPI :8000<br/>presigned URLs"]
      WRK["Worker<br/>K-Means, OpenAI"]
      REDIS["Redis :6379<br/>same EC2 host"]
    end

    FEA -->|:8000| API
    FEC -->|:8000| API
    FEA --> REDIS
    FEC --> REDIS
    API -.->|"0.0.0.0/0 NAT"| FEC
    WRK -.->|"0.0.0.0/0 NAT"| FEC
  end

  FEA -->|JWT| LAM
  FEC -->|JWT| LAM

  API -->|presigned PUT| S3U["S3 uploads/"]
  S3U --> SQS["SQS analysis-queue"]
  SQS --> WRK
  WRK --> S3R["S3 results/"]
  S3R --> COMP["Completion Lambda"]
  COMP --> DDBA["DynamoDB analyses"]
  COMP --> SNSDONE["SNS analysis-complete"]

  subgraph XCUT["Shared"]
    SM["Secrets Manager"]
    CW["CloudWatch /retaillen/*"]
    IAM["IAM roles + IMDSv2"]
  end
```

Compute is EC2 plus two Lambdas (sign-in Function URL; S3-triggered completion). Database is DynamoDB only. Secrets Manager holds secrets (not SSM).
No user groups: each account is a standalone user.
The Lambdas use execution roles (not IAM user `mike` / `AWS_PROFILE`).
SSH is EICE only; the private backend has no public IPv4.

## Address paths

Private addresses below were read from the instance ENIs on 25 September 2026. Public IPv4 on the ALB and on frontends 1A and 1C is auto-assigned, so those hops are named rather than numbered.

Inbound user traffic stops at the ALB public addresses, then uses private addresses only.

```mermaid
flowchart LR
  U[Browser] --> CF[CloudFront]
  CF --> A1["ALB public IPv4<br/>us-east-1a"]
  CF --> A2["ALB public IPv4<br/>us-east-1c"]
  A1 --> F1["Frontend 1A<br/>172.31.2.199"]
  A2 --> F2["Frontend 1C<br/>172.31.22.130"]
  F1 --> B["Backend<br/>172.31.105.54"]
  F2 --> B
```

Outbound traffic leaves from 1A's own public address, and from 1C, which also NATs `172.31.96.0/20`.

```mermaid
flowchart LR
  F1["Frontend 1A<br/>172.31.2.199"] --> P1["1A public IPv4"] --> N1[Internet]
  B["Backend<br/>172.31.105.54"] --> F2["1C<br/>172.31.22.130"] --> P2["1C public IPv4"] --> N2[Internet]
  F2 --> P2
```

Deploys do not use those public addresses. GitHub Actions enters through the Instance Connect endpoint, then SSH to the three private addresses.

```mermaid
flowchart LR
  G[GitHub Actions] --> E["EICE<br/>172.31.13.78"]
  E --> F1["Frontend 1A<br/>172.31.2.199"]
  E --> F2["Frontend 1C<br/>172.31.22.130"]
  E --> B["Backend<br/>172.31.105.54"]
```
