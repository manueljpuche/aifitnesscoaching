from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "ai-fitness-coaching"
    app_env: str = "local"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = "change-me"

    # CORS
    cors_origins: list[str] = ["https://web.telegram.org"]

    # Database
    database_url: str = "postgresql+asyncpg://fitness:fitness@localhost:5432/fitness"
    database_pool_size: int = 5
    database_max_overflow: int = 15

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 10

    # AI Provider ("openai" or "groq")
    ai_provider: str = "groq"

    # OpenAI
    openai_api_key: str = ""
    openai_model_default: str = "gpt-4o-mini"
    openai_model_advanced: str = "gpt-4o"

    # Groq (free tier)
    groq_api_key: str = ""
    groq_model_default: str = "llama-3.1-8b-instant"
    groq_model_advanced: str = "llama-3.3-70b-versatile"
    groq_model_vision: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    ai_daily_budget_usd_per_user: float = 0.50
    ai_daily_budget_total_usd: float = 10.00

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_progress_photos: str = "fitness-progress-photos"
    minio_bucket_pantry_scans: str = "fitness-pantry-scans"
    minio_bucket_voice_notes: str = "fitness-voice-notes"
    minio_bucket_exports: str = "fitness-exports"
    minio_bucket_barcode_scans: str = "fitness-barcode-scans"

    # Sentry
    sentry_dsn: str = ""
    sentry_environment: str = "local"
    sentry_sample_rate: float = 1.0

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 10080

    # Telegram
    telegram_bot_token: str = ""

    # n8n internal auth
    n8n_internal_secret: str = "change-me-n8n-secret"


settings = Settings()


def validate_settings() -> None:
    """Raise if running with insecure defaults in non-local envs."""
    if settings.app_env not in ("local", "test"):
        if settings.secret_key == "change-me":
            raise RuntimeError("secret_key must be changed for non-local environments")
        if settings.n8n_internal_secret == "change-me-n8n-secret":
            raise RuntimeError("n8n_internal_secret must be changed for non-local environments")
