# Retail Lense

Secure multi-user cloud app for small retailers: RFM + K-Means customer segmentation, plus LLM-written advice. Built for COMPX527.

## Layout

```
frontend/     Streamlit UI (accounts, reference analysis, upload, reports)
backend/      FastAPI on EC2 + background workers + ML pipeline
infra/        IAM JSON, EICE/EC2 deploy scripts, systemd units,
              CloudFormation for a new account (do not apply to 817817875692)
data/samples/ Tiny schema samples (not the full UCI dataset)
docs/         Architecture notes
```

Compute runs on **EC2**, plus an **auth Lambda** for sign-in and sign-up. Persistence is **DynamoDB + S3** (no RDS / SQL). Local auth still uses FastAPI when `AUTH_API_URL` is empty.

## Architecture

In the default VPC `vpc-0b7f1d790c744fbad` (`172.31.0.0/16`, `us-east-1`). Account `817817875692`. Demo: [www.retaillen.cloud](https://www.retaillen.cloud).

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
      REDIS["Redis :6379<br/>compose volume"]
    end

    FEA -->|:8000| API
    FEC -->|:8000| API
    FEA --> REDIS
    FEC --> REDIS
    API -.->|"route to 1C"| FEC
    WRK -.->|"route to 1C"| FEC
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
```

Browser traffic enters only through CloudFront, then the ALB in public subnets `us-east-1a` and `us-east-1c`. The ALB listener is HTTPS :443 (IAM certificate `cloudfront/retaillen-letsencrypt`, expires 24 November 2026; ACM is out of scope). It forwards to Streamlit on both frontends, with stickiness so the same browser stays on the same instance. Sign-in and sign-up go to a Lambda Function URL outside the VPC. The session for that login is stored in Redis on the backend host.

The API, worker, and Redis run on one EC2 in `backend-private-subnet` (`172.31.96.0/20`, `us-east-1d`) with no public IPv4. That subnet has its own route table. `0.0.0.0/0` points at frontend 1C's ENI, not at an Internet Gateway and not at a NAT Gateway. On 1C, source/destination check is off and `iptables` MASQUERADE rewrites traffic from `172.31.96.0/20` to 1C's public address. `retaillen-nat-sg` accepts that subnet only, and only on 1C.

Uploads use a URL signed by the backend role. The browser writes the object to S3. S3 notifies `retaillen-analysis-queue`. The worker on the same host runs RFM and K-Means, writes `results/`, and a completion Lambda marks the job done and publishes `retaillen-analysis-complete`.

Address-level inbound, egress, and deploy diagrams are in [docs/architecture.md](docs/architecture.md). `infra/cloudformation/stack.yaml` is documentation of an older layout. Do not apply it to this account.

**In scope:** EC2, Lambda, ALB, CloudFront, S3, DynamoDB, SQS, SNS, Secrets Manager, CloudWatch, IAM, EICE.

**Forbidden by the brief, and not used:** RDS and any other relational database, SageMaker, Bedrock, WAF, ACM, Shield, Inspector, Redshift, QuickSight, Device Farm.

## Security

### Network

Security groups are the boundary. The live ALB group accepts TCP 443 only from the CloudFront origin-facing prefix list `pl-3b927c52`. Application rate limits are lockout, HTTP 429, and CAPTCHA.

| Group | Inbound | Attached to |
| --- | --- | --- |
| `retaillen-alb-sg` | TCP 443 from `pl-3b927c52` | ALB |
| `retail-frontend-sg` | TCP 8501 from the ALB group | Both frontends |
| `retaillen-backend-sg` | TCP 8000 from the frontend group | Backend |
| `retaillen-redis-sg` | TCP 6379 from the frontend group | Backend (Redis on the same host) |
| `retaillen-nat-sg` | All from `172.31.96.0/20` | Frontend 1C only |
| `retaillen-ssh-sg` | TCP 22 from `retaillen-eic-sg` | All three EC2 |
| `retaillen-eic-sg` | none | EICE |

```mermaid
flowchart LR
  CF["CloudFront<br/>pl-3b927c52"] -->|443| ALB["ALB<br/>alb-sg"]
  ALB -->|8501| FE["Frontends<br/>frontend-sg"]
  FE -->|8000| API["Backend<br/>backend-sg"]
  FE -->|6379| RD["Redis<br/>redis-sg"]
  API -->|172.31.96.0/20| NAT["Frontend 1C<br/>nat-sg"]
  EICE["EICE<br/>eic-sg"] -->|22| FE
  EICE -->|22| API
```

Application security groups allow egress to `0.0.0.0/0`. That egress is how the instances reach Secrets Manager, AWS APIs, the Lambda URL, GitHub, OpenAI, and Gmail on port 587. Frontend 1A uses its own public address for that. The backend uses the 1C route above. 1A is not a second NAT.

### IAM

Instance and Lambda roles call AWS. Laptops do not hold production keys. The policy text is the JSON under `infra/iam/`. The live backend role name is `retail-ec2role`; its document is `retaillen-backend-runtime-policy.json`.

| Principal | May call |
| --- | --- |
| `retail-frontend-runtime-role` (1A and 1C) | `GetSecretValue` on `retaillen/AUTH_API_URL`, `REDIS_URL`, `REDIS_PASSWORD`, `SESSION_COOKIE_PASSWORD` only; logs on `/retaillen/frontend` |
| `retail-ec2role` (backend) | S3 get on `public/`, `uploads/`, `results/`; put and delete on `uploads/` and `results/`; DynamoDB CRUD on the five tables; SQS on `retaillen-analysis-queue`; `sns:Publish` to `retaillen-analysis-complete`, and to SMS only when `sns:Protocol` is `sms`; secrets `jwt`, `openai`, Redis, SMTP |
| `retaillen-signin-lambda` | DynamoDB on users, login-history, and otps; `sns:Publish` only when `sns:Protocol` is `sms`; `GetSecretValue` on `retaillen/jwt-*` only |
| `retail-lamdba-role` (completion) | `UpdateItem` on analyses, SNS on the completion topic, `s3:GetObject` on `results/*` |
| IAM user `github-eice` | `OpenTunnel` on EICE endpoints in this account; `SendSSHPublicKey` on instances only as OS user `mike`; `DescribeInstances` and `DescribeInstanceConnectEndpoints` only in `us-east-1` |

The live frontend role has one policy, `frontend-runtime.json`: four secrets and CloudWatch logs on `/retaillen/frontend`. It has no S3, DynamoDB, or SQS permission. The browser uploads with a presigned URL signed by `retail-ec2role`. The sign-in Lambda reads `retaillen/jwt-*` only. SMS publish is allowed only when `sns:Protocol` is `sms`. Analysis-complete publish is limited to that topic. `retail-ec2role` also has `UploadServerCertificatePolicy`, used to upload a replacement IAM server certificate when `cloudfront/retaillen-letsencrypt` is renewed. Deploys use EICE.

```mermaid
flowchart LR
  FE["retail-frontend-runtime-role"] -->|GetSecretValue| SM["Secrets Manager<br/>AUTH, Redis, cookie"]
  BE["retail-ec2role"] -->|Get Put Delete| S3["S3 retaillen-dev"]
  BE -->|CRUD| DDB["DynamoDB<br/>five tables"]
  BE -->|send / receive| SQS["analysis-queue"]
  BE -->|Publish| SNS["SNS<br/>SMS and analysis-complete"]
  BE -->|GetSecretValue| SM2["Secrets Manager<br/>jwt, openai, Redis, SMTP"]
  SL["retaillen-signin-lambda"] -->|users, history, otps| DDB
  SL -->|Publish SMS| SNS
  SL -->|GetSecretValue| SM3["Secrets Manager<br/>retaillen/jwt"]
  CL["retail-lamdba-role"] -->|UpdateItem analyses| DDB
  CL -->|Publish| SNS
  CL -->|GetObject results| S3
  CI["github-eice"] -->|OpenTunnel| EICE["EICE"]
```

### Application controls

- Passwords are bcrypt. JWT material is `retaillen/jwt` in Secrets Manager (`JWT_SECRET` is a local fallback only).
- Five failed logins lock the account for 24 hours (HTTP 423). Repeated failures from one IP return 429. An administrator can block an IP (HTTP 403). A non-admin cannot.
- Each attempt is stored in `retaillen-login-history` with the browser IP. Streamlit sends `x-retaillen-client-ip` because the Lambda URL's CloudFront hop rewrites `X-Forwarded-For`.
- SMS 2FA is optional after login. Unbound accounts sign in with a password only.
- Forgot-password emails a one-time link (48 h). Unknown addresses still return HTTP 200.
- DynamoDB user updates after login are attribute patches, so a sign-in cannot replace the row and drop `is_admin`.
- S3 keys are per-user prefixes. The UI does not list another user's prefix. Secrets are not in git. On EC2, `APP_ENV=aws` and empty secret env vars force a role read from Secrets Manager.
- IMDSv2 is required (hop limit 2) so Docker Compose can assume the instance role.

### Security considerations

Checked against the live roles on 26 September 2026, the 25 September 2026 instance metadata, and `infra/iam/*.json`.

1. **Least-privilege IAM.** `retail-frontend-runtime-role` has one customer-managed policy, `frontend-runtime.json`. It may `GetSecretValue` on four secrets only: `retaillen/AUTH_API_URL`, `REDIS_URL`, `REDIS_PASSWORD`, `SESSION_COOKIE_PASSWORD`. That policy has no S3, DynamoDB, or SQS. It may write CloudWatch logs only for `/retaillen/frontend`. `retail-ec2role` uses `retaillen-backend-runtime-policy.json`: the `public/`, `uploads/`, and `results/` prefixes, the five DynamoDB tables, `retaillen-analysis-queue`, and `sns:Publish` only when `sns:Protocol` is `sms` or the target is `retaillen-analysis-complete`. The same role has `UploadServerCertificatePolicy` so a renewed Let's Encrypt certificate can be uploaded to IAM. App containers do not receive long-lived access keys; they use the instance role. The CI user `github-eice` is a separate key, stored in GitHub Actions, and it cannot call S3 or DynamoDB.
2. **IMDSv2.** All three running instances have `HttpTokens=required` and hop limit 2. IMDSv1 is off. Hop 2 is what lets a container reach the instance role.
3. **Secrets Manager.** JWT, OpenAI, Redis, SMTP, the session-cookie password, and the sign-in Lambda URL are not in git. On EC2 those `.env` values stay empty and the instance role calls `GetSecretValue`. The sign-in Lambda reads `retaillen/jwt-*` only.
4. **Security groups.** Browsers reach CloudFront. The ALB accepts TCP 443 only from the CloudFront origin-facing prefix list `pl-3b927c52`. Only the ALB group may connect to the frontends on 8501. FastAPI 8000 accepts traffic only from the frontend group. Redis listens on 6379 on that same backend EC2; `retaillen-redis-sg` allows it only from the frontend group. `retaillen-nat-sg` allows the private subnet `172.31.96.0/20` onto 1C only.
5. **EICE, no public SSH.** Port 22 is not open to `0.0.0.0/0`. `retaillen-ssh-sg` allows TCP 22 only from `retaillen-eic-sg`, which has no inbound of its own. Operators and GitHub Actions open an Instance Connect tunnel and push a short-lived SSH key. `github-eice` may `OpenTunnel` and may `SendSSHPublicKey` only as OS user `mike`.
6. **Presigned uploads.** The browser PUTs to S3 with a URL signed by `retail-ec2role` (15 minutes). Streamlit has no `s3:PutObject`.
7. **Login protections.** Passwords are bcrypt. Five failures lock the account for 24 hours. Failures from one IP return 429. An administrator can block an IP. Sign-up uses a CAPTCHA. Forgot-password always returns HTTP 200, including for unknown addresses.
8. **Sessions.** Sign-in returns an access JWT that lasts 1 hour and a refresh token (7 days, or 14 with remember-me). Production sign-in is the Lambda; `TOKEN_TIME=1` is a Lambda environment variable, not `.env`. The Streamlit browser cookie holds a signed session id. The tokens for that session live in Redis. TLS terminates at the ALB (IAM certificate, not ACM).
9. **EBS encryption.** Root volumes are encrypted with the AWS-managed key `aws/ebs`, so Docker data and the on-disk `.env` are encrypted at rest.
10. **Private backend.** The API, worker, and Redis run in `backend-private-subnet` (`172.31.96.0/20`, `us-east-1d`) with no public IPv4. Ports 8000 and 6379 are reachable only from the frontend group inside the VPC. Egress from that subnet goes to 1C, not to an Internet Gateway.

## Python

Use **Python 3.12** (CI and Docker). `datetime.UTC` needs 3.11+. macOS Command Line Tools `python3` is often 3.9 and will fail.

```bash
python3.12 --version
# macOS if missing: brew install python@3.12
```

Create both venvs with that interpreter, not `/usr/bin/python3`:

```bash
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd frontend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Do not run the API with `frontend/.venv` (Streamlit ships uvicorn, but the `api` package lives under `backend/`).

## Local run

Copy env once:

```bash
cp .env.example .env
```

| `.env` | User store |
| --- | --- |
| `APP_ENV=local` and empty `DDB_ENDPOINT` | In-memory (lost on API restart) |
| `DDB_ENDPOINT=http://127.0.0.1:8001` | DynamoDB Local |
| `APP_ENV=aws` and empty `DDB_ENDPOINT` | Real DynamoDB in `AWS_REGION` |

Restart the API after any `.env` change (`get_settings` is cached).

### Option A — two terminals (Python)

Terminal 1 — API (from the repo root):

```bash
./infra/scripts/run_api.sh
```

Equivalent:

```bash
cd backend
PYTHONPATH=. .venv/bin/uvicorn api.main:app --reload --port 8000
```

Terminal 2 — Streamlit UI:

```bash
cd frontend
export BACKEND_URL=http://localhost:8000
.venv/bin/streamlit run main.py
```

Windows (PowerShell), from the repo root. `py -3.12` is the Python launcher; venv tools live in `Scripts`, not `bin`.

```powershell
py -3.12 -m venv backend\.venv; backend\.venv\Scripts\pip install -r backend\requirements.txt
py -3.12 -m venv frontend\.venv; frontend\.venv\Scripts\pip install -r frontend\requirements.txt
copy .env.example .env
cd backend; $env:PYTHONPATH = "."; .\.venv\Scripts\uvicorn api.main:app --reload --port 8000
```

Second terminal: `cd frontend; $env:BACKEND_URL = "http://localhost:8000"; .\.venv\Scripts\streamlit run main.py`

### Option B — Docker

```bash
docker compose up --build frontend backend worker
```

### SMTP (password reset)

Forgot-password mail goes out through an external SMTP server. Restart the API after changing `.env`. An empty `SMTP_HOST` keeps mail in memory (what pytest uses) and does not send anything.

Gmail on port 587 with STARTTLS, which is what production uses:

```
BASE_URL=http://localhost:8501
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM_NAME=Retail Lense
SMTP_FROM_EMAIL=you@gmail.com
SMTP_AUTH_STRATEGY=TLS
SMTP_USER=you@gmail.com
SMTP_PASSWORD=app-password
```

`SMTP_AUTH_STRATEGY=SSL` connects with SMTPS instead of STARTTLS. `BASE_URL` is the front of the reset link (`/Reset_Password?token=...`). On EC2 set `BASE_URL=https://www.retaillen.cloud` and leave `SMTP_USER` and `SMTP_PASSWORD` empty so the backend reads `retaillen/SMTP_USER` and `retaillen/SMTP_PASSWORD` from Secrets Manager. Unknown addresses still return HTTP 200 and send nothing.

### URLs

- UI: http://localhost:8501
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

Sidebar pages: Home, Sign in (forgot-password expander), Sign up, Reset password, Account (profile + login history), Reference, Upload.

Auth API examples:

```bash
# register
curl -s http://localhost:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"a@example.com","username":"alice","full_name":"Alice","password":"password1","password_confirm":"password1"}'

# login (OAuth2 form: POST /auth/token). If SMS 2FA is on, this returns
# {"status":"otp_required","phone_hint":"..."} instead of access_token.
curl -s http://localhost:8000/auth/token -d 'username=alice&password=password1'

# optional SMS 2FA (bind after login; not required at sign-up)
curl -s http://localhost:8000/auth/2fa/phone -H "Authorization: Bearer TOKEN" \
  -H 'Content-Type: application/json' -d '{"phone":"+64211234567"}'
curl -s http://localhost:8000/auth/2fa/confirm -H "Authorization: Bearer TOKEN" \
  -H 'Content-Type: application/json' -d '{"code":"123456"}'
curl -s http://localhost:8000/auth/verify-otp -H 'Content-Type: application/json' \
  -d '{"username":"alice","code":"123456"}'
curl -s http://localhost:8000/auth/2fa/disable -H "Authorization: Bearer TOKEN"

# login history (Bearer token)
curl -s http://localhost:8000/auth/login-history -H "Authorization: Bearer TOKEN"

# block / list / unblock an IP for this account
curl -s http://localhost:8000/auth/blocked-ips -H "Authorization: Bearer TOKEN" \
  -H 'Content-Type: application/json' -d '{"ip":"203.0.113.9"}'
curl -s http://localhost:8000/auth/blocked-ips -H "Authorization: Bearer TOKEN"
curl -s -X DELETE http://localhost:8000/auth/blocked-ips -H "Authorization: Bearer TOKEN" \
  -H 'Content-Type: application/json' -d '{"ip":"203.0.113.9"}'

# forgot password (always 200; email exists or not)
curl -s http://localhost:8000/users/forgot-password -H 'Content-Type: application/json' \
  -d '{"email":"a@example.com"}'

# reset password (token from the email link)
curl -s http://localhost:8000/users/reset-password -H 'Content-Type: application/json' \
  -d '{"token":"TOKEN","email":"a@example.com","password":"password2","passwordConfirm":"password2"}'
```

Backend tests:

```bash
cd backend && PYTHONPATH=. pytest tests/
```

## DynamoDB (local or AWS)

Auth (users, login history, reset tokens, OTPs, analyses) is stored in DynamoDB. The worker consumes SQS and writes results to S3.

### Local — DynamoDB Local (no AWS account)

Users still need a database, or register and forgot-password vanish when the API restarts. The DynamoDB Local service in `docker-compose.yml` is commented out; uncomment it before the command below.

```bash
# 1. start the local DynamoDB (host port 8001 — 8000 is the API)
docker compose up -d dynamodb

# 2. point the API at it (repo-root .env)
#    DDB_ENDPOINT=http://127.0.0.1:8001
#    APP_ENV can stay local

# 3. create tables on that endpoint
./infra/scripts/create_dynamodb_tables.sh --yes

# 4. restart the backend, then check
curl -s http://localhost:8000/health
# expect: "store":"dynamodb","ddb_endpoint":"http://127.0.0.1:8001"
```

If **backend and DynamoDB both run in Compose**, the backend service already sets `DDB_ENDPOINT=http://dynamodb:8000`. Create tables from the host with `DDB_ENDPOINT=http://127.0.0.1:8001` (published port).

Stop later with `docker compose stop dynamodb`. Data lives in the `dynamodb-data` Docker volume.

### AWS account — real tables

Clear `DDB_ENDPOINT` and set `APP_ENV=aws`. Does not call STS. On-demand billing. Re-run is a no-op for tables that already exist.

```
APP_ENV=aws
AWS_REGION=us-east-1
DDB_ENDPOINT=
```

```bash
# preview
./infra/scripts/create_dynamodb_tables.sh --dry-run

# create missing tables (prompts for confirm)
./infra/scripts/create_dynamodb_tables.sh

# non-interactive
./infra/scripts/create_dynamodb_tables.sh --yes
```

Then restart the API and check:

```bash
curl -s http://localhost:8000/health
# expect: {"status":"ok","store":"dynamodb"}  — no ddb_endpoint
```

#### AWS credentials and `AWS_PROFILE`

Boto3 uses the default chain: env keys → `~/.aws/credentials` **`[default]`** → EC2 instance role.

If the machine has **several profiles** and `[default]` is the wrong IAM user, set the course profile in `.env`:

```
AWS_PROFILE=your-profile-name
```

List names with `aws configure list-profiles`. On a laptop, omit `AWS_PROFILE` when `[default]` is already the course account. On backend EC2 omit it entirely (do not write `AWS_PROFILE=`) so containers use instance role `retail-ec2role`. A blank value or a named profile that is not in the container is stripped and boto3 falls through to that role.

Do not put access keys in `.env`. A process-level `AWS_PROFILE=...` overrides `.env` (`setdefault`). Restart the API after changing it.

One-off for the table script: `AWS_PROFILE=your-profile AWS_REGION=us-east-1 ./infra/scripts/create_dynamodb_tables.sh --yes`

### Sign-in Lambda

The live function was deployed with `infra/scripts/deploy_signin_lambda.sh` (no API Gateway). `infra/cloudformation/stack.yaml` can create the same function in a new account. Farhan should attach `infra/iam/signin-lambda-deployer.json` if the current profile cannot create the function.

```bash
export AWS_PROFILE=mike-assume-infra AWS_REGION=us-east-1
./infra/scripts/deploy_signin_lambda.sh
```

Set `JWT_SECRET_NAME=retaillen/jwt` and `TOKEN_TIME=1` on the sign-in Lambda. The access token lifetime is that environment variable. Production sign-in does not read `.env`. Set `JWT_SECRET_NAME=retaillen/jwt` on backend EC2 as well. Their execution roles need `secretsmanager:GetSecretValue` for that secret; do not put the secret value in an AWS environment variable. On EC2 leave `AUTH_API_URL`, `REDIS_URL`, `REDIS_PASSWORD`, and `SESSION_COOKIE_PASSWORD` out of `.env` — Streamlit reads Secrets Manager `retaillen/<ENV_VAR>` via instance profile `retail-frontend-runtime-role`. Locally keep those four values in `.env` so a laptop `AWS_PROFILE` never fetches production secrets. The same Lambda handles `POST /auth/signin` and `POST /auth/register`. Leave `AUTH_API_URL` empty locally so auth stays on FastAPI. The function uses role `retaillen-signin-lambda`, not `AWS_PROFILE`. `GET /auth/login-history` stays on FastAPI.

## Production (EC2)

A merge to **`dev`** deploys application code with GitHub Actions over the EC2 Instance Connect Endpoint. `infra/scripts/deploy.sh` creates a **new** CloudFormation stack only when `CONFIRM=deploy`. It refuses account `817817875692`, where the VPC, ALB, and instances already exist. Deploys do not use SSM.

Live images: frontend 1C is Ubuntu 26.04. Frontend 1A is Amazon Linux 2023 (`al2023-ami-ecs-neuron`). The backend instance uses the custom AMI `retaillen-backend-private`. A new stack from `infra/cloudformation/stack.yaml` launches Ubuntu 26.04.

App directories on the instances: frontend `/home/mike/retail-lense`, backend `/home/mike/retail-lense/retail-lense`. Both run Docker Compose, not the systemd units.

### One-time on the instance

User `mike`. Install Docker and the Compose plugin, then clone the repo and check out `dev`. Copy `.env` onto the box only (`APP_ENV=aws`, empty `DDB_ENDPOINT`). Backend uses `retail-ec2role`. Each frontend uses `retail-frontend-runtime-role`. Leave `AUTH_API_URL`, Redis, and the session-cookie secret out of `.env`.

Allow GitHub Actions to reach the instances through the EC2 Instance Connect Endpoint (no public port 22). Attach `infra/iam/github-eice.json` to IAM user `github-eice` (the keys in `DEPLOY_AWS_*`).

### GitHub Actions secrets

| Secret | Example |
| --- | --- |
| `DEPLOY_HOST_BACKEND_US_1D` | Backend instance id in `us-east-1d` |
| `DEPLOY_HOST_FRONTEND_US_1A` | Frontend instance id in `us-east-1a` |
| `DEPLOY_HOST_FRONTEND_US_1C` | Frontend instance id in `us-east-1c` |
| `DEPLOY_EICE_ENDPOINT_ID` | One EICE id for backend and both frontend instances, e.g. `eice-05b0600db42072e83` |
| `DEPLOY_USER` | `mike` |
| `DEPLOY_AWS_ACCESS_KEY_ID` | IAM access key that can use Instance Connect Endpoint |
| `DEPLOY_AWS_SECRET_ACCESS_KEY` | Matching secret key |

A merge into **`dev`** (or a direct push to `dev`) runs tests, then deploys only the stack that changed: `backend/**` → backend EC2 in `US_1D`; `frontend/**` → **both** frontend instances (`US_1A` and `US_1C`) in parallel (each box `git fetch` + `git reset --hard origin/dev` + restart Streamlit). A `docker-compose.yml` change deploys backend and both frontends. Manual: Actions → CI/CD → Run workflow (deploys all). Production/`master` is not wired yet.

Backend and both frontend instances share `DEPLOY_EICE_ENDPOINT_ID`.

On a frontend-only instance, set `BACKEND_URL` in `.env` to the backend private address (not `http://backend:8000`). Attach only `retail-frontend-runtime-role`. Omit `AUTH_API_URL` / `REDIS_URL` / `REDIS_PASSWORD` / `SESSION_COOKIE_PASSWORD` from `.env` so Streamlit reads `retaillen/<ENV_VAR>`. Compose does not pass `AWS_PROFILE` or access keys into the Streamlit container. The frontend deploy uses `docker compose up --no-deps` so it does not start the API or Redis on that box.

## Dataset

Public reference analysis uses the [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail) schema: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`.

## Conventions

All comments, docstrings, README/docs Markdown, and inline notes in this repository must be written in English.


ONLINE DEMO: https://www.retaillen.cloud

CloudFront, without the domain registrar: https://d1ncltjzzrscfi.cloudfront.net


