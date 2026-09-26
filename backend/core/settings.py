"""Application settings. Secrets come from env locally, Secrets Manager on EC2."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _load_repo_dotenv() -> None:
    """Load repo-root .env into os.environ. Existing process env wins."""
    path = Path(__file__).resolve().parents[2] / ".env"
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            os.environ.setdefault(key, value)


def _drop_blank_aws_profile() -> None:
    from core.aws import drop_blank_aws_profile

    drop_blank_aws_profile()


_load_repo_dotenv()
_drop_blank_aws_profile()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return default if raw is None or raw == "" else int(raw)


class Settings:
    app_env: str
    allow_signup: bool
    jwt_secret_name: str
    jwt_secret: str
    jwt_algorithm: str
    token_time_hours: int
    remember_me_days: int
    issuer: str
    security_max_login_attempts: int
    security_user_lockout_hours: int
    security_max_failed_per_ip: int
    security_ip_window_minutes: int
    aws_region: str
    aws_profile: str
    s3_bucket: str
    s3_prefix_public: str
    s3_transactions_sample_key: str
    ddb_endpoint: str
    ddb_users_table: str
    ddb_login_history_table: str
    ddb_password_reset_table: str
    ddb_otps_table: str
    sns_sms_enabled: bool
    otp_ttl_seconds: int
    otp_resend_seconds: int
    otp_max_attempts: int
    # Analyses table + S3/SQS/SNS/OpenAI config for the upload -> worker -> Lambda pipeline.
    ddb_analyses_table: str
    s3_prefix_uploads: str
    s3_prefix_results: str
    sqs_analysis_queue_url: str
    sns_analysis_complete_topic_arn: str
    openai_secret_name: str
    openai_model: str
    analysis_k: int
    base_url: str
    password_reset_path: str
    password_reset_token_hours: int
    smtp_host: str
    smtp_port: int
    smtp_from_name: str
    smtp_from_email: str
    smtp_user: str
    smtp_password: str
    smtp_auth_strategy: str
    max_upload_mb: int


    def is_local(self) -> bool:
        return self.app_env in {"local", "test"}

    def uses_dynamodb(self) -> bool:
        if self.app_env == "test":
            return False
        if self.ddb_endpoint:
            return True
        return self.app_env == "aws"

    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_from_email)

    def password_reset_url(self, token: str) -> str:
        path = (self.password_reset_path or "/Reset_Password").strip()
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path.rstrip('/')}?token={token}"


def _load_jwt_secret(app_env: str, secret_name: str) -> str:
    if app_env == "aws":
        if not secret_name:
            raise RuntimeError("JWT_SECRET_NAME is required when APP_ENV=aws")
        from services.secrets import get_secret

        return get_secret(secret_name)
    return os.getenv("JWT_SECRET") or os.getenv("SECRET") or "local-dev-only-change-me"


def _load_smtp_secret(env_key: str, settings: Settings) -> str:
    value = os.getenv(env_key, "").strip()
    if value:
        return value
    if settings.app_env != "aws" or not settings.smtp_enabled():
        return ""
    if (settings.smtp_auth_strategy or "TLS").upper() == "NONE":
        return ""
    from services.secrets import get_secret

    return get_secret(f"retaillen/{env_key}", field=env_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    _drop_blank_aws_profile()
    settings.app_env = os.getenv("APP_ENV", "aws")
    settings.allow_signup = _bool("ALLOW_SIGNUP", True)
    settings.jwt_secret_name = os.getenv("JWT_SECRET_NAME", "").strip()
    settings.jwt_secret = _load_jwt_secret(settings.app_env, settings.jwt_secret_name)
    settings.jwt_algorithm = "HS256"
    settings.token_time_hours = max(1, _int("TOKEN_TIME", 48))
    settings.remember_me_days = _int("REMEMBER_ME_DAYS", 14)
    settings.issuer = os.getenv("JWT_ISSUER", "retaillen")
    settings.security_max_login_attempts = _int("SECURITY_MAX_LOGIN_ATTEMPTS", 5)
    settings.security_user_lockout_hours = _int("SECURITY_USER_LOCKOUT_TIME", 24)
    settings.security_max_failed_per_ip = _int("SECURITY_MAX_FAILED_PER_IP", 20)
    settings.security_ip_window_minutes = _int("SECURITY_IP_WINDOW_MINUTES", 15)
    settings.aws_region = os.getenv("AWS_REGION", "us-east-1")
    settings.aws_profile = os.getenv("AWS_PROFILE", "").strip()
    settings.s3_bucket = os.getenv("S3_BUCKET", "retaillen-dev").strip()
    settings.max_upload_mb = _int("MAX_UPLOAD_MB", 25)
    prefix = os.getenv("S3_PREFIX_PUBLIC", "public/").strip() or "public/"
    if not prefix.endswith("/"):
        prefix = f"{prefix}/"
    settings.s3_prefix_public = prefix
    settings.s3_transactions_sample_key = (
        os.getenv("S3_TRANSACTIONS_SAMPLE_KEY", "").strip()
        or f"{prefix}transactions_sample.csv"
    )
    settings.ddb_endpoint = os.getenv("DDB_ENDPOINT", "").rstrip("/")
    settings.ddb_users_table = os.getenv("DDB_USERS_TABLE", "retaillen-users")
    settings.ddb_login_history_table = os.getenv("DDB_LOGIN_HISTORY_TABLE", "retaillen-login-history")
    settings.ddb_password_reset_table = os.getenv("DDB_PASSWORD_RESET_TABLE", "retaillen-password-reset")
    settings.ddb_otps_table = os.getenv("DDB_OTPS_TABLE", "retaillen-otps")
    settings.sns_sms_enabled = _bool("SNS_SMS_ENABLED", False)
    settings.otp_ttl_seconds = max(60, _int("OTP_TTL_SECONDS", 300))
    settings.otp_resend_seconds = max(15, _int("OTP_RESEND_SECONDS", 60))
    settings.otp_max_attempts = max(1, _int("OTP_MAX_ATTEMPTS", 5))
    # Analyses pipeline: table name, S3 prefixes, SQS queue, SNS topic, OpenAI secret/model, fixed k.
    settings.ddb_analyses_table = os.getenv("DDB_ANALYSES_TABLE", "retaillen-analyses")
    uploads_prefix = os.getenv("S3_PREFIX_UPLOADS", "uploads/").strip() or "uploads/"
    if not uploads_prefix.endswith("/"):
        uploads_prefix = f"{uploads_prefix}/"
    settings.s3_prefix_uploads = uploads_prefix
    results_prefix = os.getenv("S3_PREFIX_RESULTS", "results/").strip() or "results/"
    if not results_prefix.endswith("/"):
        results_prefix = f"{results_prefix}/"
    settings.s3_prefix_results = results_prefix
    settings.sqs_analysis_queue_url = os.getenv("SQS_ANALYSIS_QUEUE_URL", "").strip()
    settings.sns_analysis_complete_topic_arn = os.getenv("SNS_ANALYSIS_COMPLETE_TOPIC_ARN", "").strip()
    settings.openai_secret_name = os.getenv("OPENAI_SECRET_NAME", "retaillen/openai").strip()
    settings.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    settings.analysis_k = _int("ANALYSIS_K", 4)
    settings.base_url = os.getenv("BASE_URL", "http://localhost:8501").rstrip("/")
    settings.password_reset_path = os.getenv("PASSWORD_RESET_PATH", "/Reset_Password")
    settings.password_reset_token_hours = max(1, _int("PASSWORD_RESET_TOKEN_HOURS", 48))
    settings.smtp_host = os.getenv("SMTP_HOST", "")
    settings.smtp_port = _int("SMTP_PORT", 587)
    settings.smtp_from_name = os.getenv("SMTP_FROM_NAME", "Retail Lense")
    settings.smtp_from_email = os.getenv("SMTP_FROM_EMAIL", "")
    settings.smtp_auth_strategy = os.getenv("SMTP_AUTH_STRATEGY", "TLS")
    settings.smtp_user = _load_smtp_secret("SMTP_USER", settings)
    settings.smtp_password = _load_smtp_secret("SMTP_PASSWORD", settings)
    return settings
