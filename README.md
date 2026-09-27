# Retail Lense

A web app that turns a retailer's invoice file into customer segments and short written advice.

Live demo: [www.retaillen.cloud](https://www.retaillen.cloud)

## Features

- Sign up with a CAPTCHA, sign in, optional SMS two-factor, and password reset.
- A public reference report on the [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail) column schema.
- Private CSV or Excel upload. The pipeline cleans the file, computes RFM, runs K-Means, and asks a language model for retention advice.
- An analysis library for past uploads.

Architecture, security groups, and IAM are in [docs/architecture.md](docs/architecture.md). How a push to `dev` is deployed is in [docs/automation_report.md](docs/automation_report.md).

## Installation

Python 3.12. The system `python3` on macOS is often 3.9 and will fail.

```bash
python3.12 --version
cp .env.example .env
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd ../frontend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Windows (PowerShell), from the repo root:

```powershell
py -3.12 -m venv backend\.venv; backend\.venv\Scripts\pip install -r backend\requirements.txt
py -3.12 -m venv frontend\.venv; frontend\.venv\Scripts\pip install -r frontend\requirements.txt
copy .env.example .env
```

Docker instead of the two venvs:

```bash
cp .env.example .env
docker compose up --build frontend backend worker
```

Leave `AUTH_API_URL` empty in `.env` so local sign-in stays on FastAPI. Do not commit `.env`.

## Usage

Two terminals, from the repo root:

```bash
./infra/scripts/run_api.sh
```

```bash
cd frontend
export BACKEND_URL=http://localhost:8000
.venv/bin/streamlit run main.py
```

- UI: http://localhost:8501
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

With `APP_ENV=local` and an empty `DDB_ENDPOINT`, accounts live in memory and disappear when the API restarts. For a local database, uncomment the `dynamodb` service in `docker-compose.yml`, then:

```bash
docker compose up -d dynamodb
# set DDB_ENDPOINT=http://127.0.0.1:8001 in .env
./infra/scripts/create_dynamodb_tables.sh --yes
```

Restart the API after any `.env` change. Backend tests:

```bash
cd backend && PYTHONPATH=. pytest tests/
```

## Contributing

Open pull requests against `dev`. A pull request runs the tests. A push to `dev` deploys. `master` does not. Comments, docstrings, and docs in this repository are in English.

## License

This repository has no license file. It is a COMPX527 course project.
