# Frontend development guide

This UI is **Streamlit**, not a React/Vue/static site. There is no `index.html`, no `src/` of `.js` files, and no stylesheet folder.

Streamlit turns Python `st.*` calls into the HTML/CSS/JS that the browser shows. You edit **Python pages** and a little CSS in two places below.

## Where HTML / CSS / JS actually live

| What you are looking for | Where it is |
| --- | --- |
| Page layout / forms / text | `app.py` and `pages/*.py` (`st.title`, `st.form`, `st.button`, …) |
| Theme (colors, font) | `.streamlit/config.toml` |
| Extra CSS (width, hide Streamlit chrome) | `components/style.py` (`_CSS`) |
| Client-side JavaScript | None in this repo. Streamlit ships its own. Do not add a `script.js`. |
| HTTP to the API | `services/api_client.py` |
| Login state (JWT) | `services/session.py` |

To change copy or a form, open the page `.py`. To change colors, edit `config.toml`. To change spacing or hide the Streamlit menu, edit `_CSS` in `style.py`.

## Layout

```
frontend/
  app.py                      Home  →  http://localhost:8501/
  pages/
    1_Login.py                →  /Login
    2_Sign_Up.py              →  /Sign_Up
    3_Reset_Password.py       →  /Reset_Password
    4_Account.py              →  /Account
    5_Reference.py            →  /Reference
    6_Upload.py               →  /Upload
  components/
    style.py                  page chrome + injected CSS
    charts.py                 RFM / cluster charts (stub)
    upload.py                 file uploader widget (stub; not wired into 6_Upload yet)
    auth_ui.py                unused
  services/
    api_client.py             httpx calls to FastAPI
    session.py                access_token + user in st.session_state
  .streamlit/config.toml      theme + server port 8501
  requirements.txt
  Dockerfile
```

The number prefix on a page file is **sidebar order only**. The URL is the rest of the name: `1_Login.py` → `/Login`.

## Run locally

Needs Python 3.12 and the API on port 8000.

```bash
cd frontend
export BACKEND_URL=http://localhost:8000
.venv/bin/streamlit run app.py
```

UI: http://localhost:8501

The API must be running separately (`./infra/scripts/run_api.sh` from the repo root). Streamlit does not use boto3. Sign-in and sign-up go to FastAPI unless `AUTH_API_URL` is set to the Lambda Function URL. Login history is always FastAPI `GET /auth/login-history`.

## How a page is built

Every page follows the same pattern:

```python
from components.style import setup
from services import api_client, session

setup("Sign in")          # title + CSS + sidebar caption
st.title("Sign in")       # visible heading
# st.form / st.button / st.write ...
```

`setup()` must run before other Streamlit widgets.

Common widgets used here:

- `st.form` + `st.form_submit_button` — login, register, reset password
- `st.button` — sign out, send reset link, block IP
- `st.error` / `st.success` / `st.caption` — feedback
- `st.stop()` — halt the page (e.g. not signed in)
- `st.rerun()` — refresh after login / sign-out

## Styling

**Theme** (`.streamlit/config.toml`):

- `primaryColor`, `backgroundColor`, `textColor`, `font`

**Injected CSS** (`components/style.py`):

- hides Streamlit menu / footer / header
- caps content width at 640px
- sidebar background

There is no CSS module system. Keep extra CSS in `_CSS`. Comments and docs in this repo stay English.

## Talking to the backend

`services/api_client.py` is the only HTTP layer. Base URL: `BACKEND_URL` (default `http://localhost:8000`).

| UI action | Function | API |
| --- | --- | --- |
| Sign up | `register` | `POST /auth/register` (or `AUTH_API_URL/auth/register`) |
| Sign in | `signin` | `POST /auth/signin` (or `AUTH_API_URL/auth/signin`) |
| Current user | `me` | `GET /users/me` |
| Forgot password | `forgot_password` | `POST /users/forgot-password` |
| Reset password | `reset_password` | `POST /users/reset-password` |
| Login history | `login_history` | `GET /auth/login-history` |
| Block / unblock IP | `block_ip` / `unblock_ip` | `/auth/blocked-ips` |
| CSV template | `transactions_sample` | `GET /uploads/transactions-sample` |

Without Redis, JWT is stored only in `st.session_state["access_token"]`. With
Redis enabled, the JWT is stored in Redis and the cookie contains only an
encrypted random session ID.

On EC2, systemd sets `BACKEND_URL=http://127.0.0.1:8000` (`infra/systemd/retaillen-ui.service`).

## Shared sessions on two EC2 instances

When `REDIS_URL` is configured, Streamlit stores the JWT and user record in
Redis. The browser receives only an encrypted random session ID. Both
Streamlit instances must use the same `REDIS_URL` and
`SESSION_COOKIE_PASSWORD`.

Run the Redis Compose profile on exactly one EC2 instance:

```bash
docker compose --profile session-store up -d redis
```

Set `REDIS_URL=redis://:password@<redis-private-ip>:6379/0` on both EC2
instances, then recreate both frontend containers. Restrict security group
port 6379 to the application EC2 security group. This single-host Redis
design has no automatic failover.

## Adding a new page

1. Create `pages/7_Reports.py` (next number = next sidebar slot).
2. Call `setup("Reports")` first.
3. Put widgets in that file. Import `api_client` / `session` if you need the API or auth.
4. Restart Streamlit (or save — it usually reloads). The route will be `/Reports`.

Do not add a `.html` file for a new screen.

## What is still a stub

| File | Status |
| --- | --- |
| `pages/5_Reference.py` | Placeholder copy |
| `pages/6_Upload.py` | Sample CSV download works; analysis upload is not connected |
| `components/upload.py` | Uploader widget exists but `6_Upload.py` does not call it |
| `components/charts.py` | No Plotly charts yet |
| `components/auth_ui.py` | Empty; pages build their own forms |

## Do / don't

- Do edit `pages/*.py` for UI text and forms.
- Do put new API calls in `api_client.py`, not inside a page with raw `httpx`.
- Do not create `index.html`, `app.js`, or a `static/` CSS tree for the main UI.
- Do not call AWS (S3/DynamoDB) from Streamlit. The backend owns that.
- Do not run the API with `frontend/.venv` — the `api` package lives under `backend/`.
