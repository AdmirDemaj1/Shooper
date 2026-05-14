import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # FastAPI
    FASTAPI_ENV: str = os.getenv("FASTAPI_ENV", "dev")
    DEBUG: bool = FASTAPI_ENV == "dev"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/autoscout_dev"
    )
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "20"))
    DATABASE_ECHO: bool = FASTAPI_ENV == "dev"

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))

    # Firebase
    FIREBASE_CREDENTIALS: str = os.getenv("FIREBASE_CREDENTIALS", "{}")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "autoscout-dev")

    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Twilio
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_PHONE_NUMBER: str = os.getenv("TWILIO_WHATSAPP_PHONE_NUMBER", "")

    # Observability
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
