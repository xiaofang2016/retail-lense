# Retail Lense

Secure multi-user cloud app for small retailers: RFM + K-Means customer segmentation, plus LLM-written advice. Built for COMPX527.

## Layout

```
frontend/     Streamlit UI (accounts, reference analysis, upload, reports)
backend/      FastAPI on EC2 + background workers + ML pipeline
infra/        CloudFormation and deploy scripts
data/samples/ Tiny schema samples (not the full UCI dataset)
docs/         Architecture notes
```

Compute runs on **EC2**, plus an **auth Lambda** for sign-in and sign-up. Persistence is **DynamoDB + S3** (no RDS / SQL). Local auth still uses FastAPI when `AUTH_API_URL` is empty.

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
.venv/bin/streamlit run app.py
```

### Option B — Docker

Skip the analysis worker for now (it is still a stub):

```bash
docker compose up --build frontend backend
```

### Local email (Mailpit)

Forgot-password emails go to a local catch-all inbox, not a real mailbox. [Mailpit](https://mailpit.axllent.org/) listens on SMTP **1025** and serves the inbox UI on **8025**. Official install notes: https://mailpit.axllent.org/docs/install/

#### 1. Install and start Mailpit

**Recommended — Docker Compose** (image is already in `docker-compose.yml`):

```bash
# needs Docker Desktop (or another Docker engine) running
docker compose up -d mailpit
docker compose ps mailpit
```

Stop later with `docker compose stop mailpit`. Remove the container with `docker compose down`.

**macOS — Homebrew** (no Docker):

```bash
brew install mailpit
mailpit
```

Leave that process running. Default ports are the same: SMTP `127.0.0.1:1025`, UI `http://127.0.0.1:8025`.

**Standalone binary** (Linux / other): download a release from https://github.com/axllent/mailpit/releases and run `./mailpit`.

#### 2. Point the API at Mailpit

Put this in the repo-root `.env`, then **restart the backend** so settings reload:

```
SMTP_HOST=127.0.0.1
SMTP_PORT=1025
SMTP_FROM_EMAIL=noreply@retaillen.local
SMTP_AUTH_STRATEGY=NONE
```

If **backend and Mailpit both run in Compose**, use the service name instead of localhost:

```
SMTP_HOST=mailpit
SMTP_PORT=1025
SMTP_FROM_EMAIL=noreply@retaillen.local
SMTP_AUTH_STRATEGY=NONE
```

Leave `SMTP_HOST` empty to keep the in-memory outbox (what the pytest suite uses).

On EC2 with real SMTP (`SMTP_AUTH_STRATEGY` not `NONE`), leave `SMTP_USER` and `SMTP_PASSWORD` empty so backend reads `retaillen/SMTP_USER` and `retaillen/SMTP_PASSWORD`.

#### 3. Check the inbox

1. Open http://localhost:8025 — you should see an empty Mailpit inbox.
2. In the UI, **Sign in → Forgot password → Send reset link** (use a registered email).
3. The message appears in Mailpit. The reset link is `http://localhost:8501/Reset_Password?token=...` (Streamlit page `pages/3_Reset_Password.py`, not a FastAPI route).
4. Unknown emails still return HTTP 200 and **do not** send a message (anti-enumeration).

### URLs

- UI: http://localhost:8501
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Mailpit inbox: http://localhost:8025

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

Auth (users, login history, reset tokens) is stored in DynamoDB. Analyses/OTP tables are created now; the analysis workers still write stubs.

### Local — DynamoDB Local (no AWS account)

Mailpit is only SMTP. Users still need a database, or register / forgot-password vanish when the API restarts.

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

List names with `aws configure list-profiles`. On a laptop, omit `AWS_PROFILE` when `[default]` is already the course account. On backend EC2 omit it entirely (do not write `AWS_PROFILE=`) so containers use instance role `retaillen-backend-runtime`. A blank value or a named profile that is not in the container is stripped and boto3 falls through to that role.

Do not put access keys in `.env`. A process-level `AWS_PROFILE=...` overrides `.env` (`setdefault`). Restart the API after changing it.

One-off for the table script: `AWS_PROFILE=your-profile AWS_REGION=us-east-1 ./infra/scripts/create_dynamodb_tables.sh --yes`

### Sign-in Lambda

No CloudFormation and no API Gateway. Deploy with the AWS CLI (or the console steps in `infra/scripts/deploy_signin_lambda.sh`). Farhan should attach `infra/iam/signin-lambda-deployer.json` if the current profile cannot create the function.

```bash
export AWS_PROFILE=mike-assume-infra AWS_REGION=us-east-1
./infra/scripts/deploy_signin_lambda.sh
```

Set `JWT_SECRET_NAME=retaillen/jwt` on Lambda and backend EC2. Their execution roles need `secretsmanager:GetSecretValue` for that secret; do not put the secret value in an AWS environment variable. On EC2 leave `AUTH_API_URL`, `REDIS_URL`, `REDIS_PASSWORD`, and `SESSION_COOKIE_PASSWORD` out of `.env` — Streamlit reads Secrets Manager `retaillen/<ENV_VAR>` via instance role `retaillen-frontend-runtime`. Locally keep those four values in `.env` so a laptop `AWS_PROFILE` never fetches production secrets. The same Lambda handles `POST /auth/signin` and `POST /auth/register`. Leave `AUTH_API_URL` empty locally so auth stays on FastAPI. The function uses role `retaillen-signin-lambda`, not `AWS_PROFILE`. `GET /auth/login-history` stays on FastAPI.

## Production (EC2, Amazon Linux)

CloudFormation (`infra/scripts/deploy.sh`) is still a stub. The SSH pipeline below is the **test environment**: a merge (push) to **`dev`** deploys immediately. No SSM.

### One-time on the instance

Amazon Linux as user `mike`. App dir: `/home/mike/retail-lense`.

```bash
sudo dnf install -y git python3.12 python3.12-pip

# Deploy key: GitHub repo → Settings → Deploy keys (read-only)
mkdir -p ~/.ssh
# put the private key in ~/.ssh/id_ed25519 (chmod 600)
ssh-keyscan github.com >> ~/.ssh/known_hosts

cd /home/mike/retail-lense
git checkout dev

python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
python3.12 -m venv frontend/.venv
frontend/.venv/bin/pip install -r frontend/requirements.txt

# Repo-root .env stays on the box only (APP_ENV=aws, empty DDB_ENDPOINT).
# Backend EC2 uses instance role retaillen-backend-runtime (no AWS_PROFILE).
# Frontend EC2: instance role retaillen-frontend-runtime only.
# edit .env: BASE_URL, SMTP, JWT_SECRET_NAME; omit AUTH_API_URL / Redis / cookie secrets.

sudo cp infra/systemd/retaillen-api.service infra/systemd/retaillen-ui.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now retaillen-api retaillen-ui
curl -s http://127.0.0.1:8000/health
```

Give `mike` passwordless restart (once):

```bash
echo 'mike ALL=(root) NOPASSWD: /bin/systemctl restart retaillen-api, /bin/systemctl restart retaillen-ui, /bin/systemctl is-active retaillen-api, /bin/systemctl is-active retaillen-ui, /bin/systemctl status retaillen-api' | sudo tee /etc/sudoers.d/retaillen
sudo chmod 440 /etc/sudoers.d/retaillen
```

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

On a frontend-only instance, set `BACKEND_URL` in `.env` to the backend host or ALB (not `http://backend:8000`). Attach only `retaillen-frontend-runtime`. Omit `AUTH_API_URL` / `REDIS_URL` / `REDIS_PASSWORD` / `SESSION_COOKIE_PASSWORD` from `.env` so Streamlit reads `retaillen/<ENV_VAR>`. Compose does not pass `AWS_PROFILE` or access keys into the Streamlit container. The frontend deploy uses `docker compose up --no-deps` so it does not start the API on that box.

Port **80** needs root (or `setcap`). Better: Streamlit on 8501, ALB/nginx on 80.

Do not `docker compose up backend` if you want AWS DynamoDB — Compose sets `DDB_ENDPOINT=http://dynamodb:8000`.


## AWS services in scope

| Service | Role |
| --- | --- |
| EC2 | Streamlit + FastAPI + analysis workers |
| Lambda | Sign-in and sign-up via one Function URL; PutItem users and login history |
| ALB | HTTPS termination, traffic distribution |
| S3 | Public UCI sample, per-user uploads, exported reports |
| DynamoDB | Users, login history, password-reset tokens, OTPs, analysis metadata |
| IAM | Least-privilege instance role and per-member roles |
| CloudWatch | Logs, metrics, billing alarms |
| SNS | SMS OTP + analysis-complete notifications |
| Secrets Manager | JWT, OpenAI, `retaillen/AUTH_API_URL`, Redis, session cookie |
| SQS (optional) | Decouple upload from clustering on EC2 |
| CloudFront (optional) | CDN in front of the ALB |

**Assignment forbids:** RDBMS, SageMaker, Bedrock, WAF, ACM, Device Farm, Redshift, QuickSight, Shield, Inspector.

**This repo does not use:** SSM. Secrets live in Secrets Manager (`JWT_SECRET` is a local-only fallback). Sign-in and sign-up can run on Lambda; IAM user `mike` needs `infra/iam/signin-lambda-deployer.json` to deploy it.

## Analysis flow

1. Signed-in user uploads CSV/Excel matching the required schema.
2. FastAPI stores the file in S3 under `uploads/{user_id}/` and writes an `Analyses` item in DynamoDB.
3. An EC2 worker validates the file, runs RFM + K-Means, stores results in S3, updates DynamoDB, and publishes SNS.

## Security notes

- Passwords hashed with bcrypt; JWT from Secrets Manager (or `JWT_SECRET` locally).
- Failed logins increment a per-user counter; after 5 failures the account is locked for 24 hours (423).
- Optional SMS 2FA: bind a phone on Account after login. Unbound accounts still sign in with password only.
- Forgot-password emails a one-time link (48h). Unknown emails still return 200.
- Every attempt is stored as login history with client IP (`X-Forwarded-For` when present).
- An account owner can block an IP; later sign-ins from that IP to that account return 403.
- Too many failures from one IP return 429.
- Streamlit talks to FastAPI, Redis, and (on EC2 only) Secrets Manager `retaillen/<ENV_VAR>`.
- Per-user S3 prefixes; results private to the owning account.
- No secrets in git.

## Dataset

Public reference analysis uses the [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail) schema: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`.

## Conventions

All comments, docstrings, README/docs Markdown, and inline notes in this repository must be written in English.
