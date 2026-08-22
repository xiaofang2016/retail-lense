"""FastAPI app hosted on EC2 behind the ALB. No Lambda."""

from fastapi import FastAPI

from api.routers import analyses, auth, reports, uploads, users
from core.settings import get_settings

app = FastAPI(title="Retail Lense API", version="0.1.0")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
app.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    payload = {
        "status": "ok",
        "store": "dynamodb" if settings.uses_dynamodb() else "memory",
    }
    if settings.ddb_endpoint:
        payload["ddb_endpoint"] = settings.ddb_endpoint
    return payload
