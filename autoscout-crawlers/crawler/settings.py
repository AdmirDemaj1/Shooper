import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/autoscout_dev"
    )
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CRAWL_SOURCES: str = os.getenv("CRAWL_SOURCES", "merrjep")
    CRAWL_SCHEDULE_MINUTE: str = os.getenv("CRAWL_SCHEDULE_MINUTE", "0")
    CRAWL_SCHEDULE_HOUR: str = os.getenv("CRAWL_SCHEDULE_HOUR", "6")

    @property
    def crawl_sources(self) -> list[str]:
        return [s.strip() for s in self.CRAWL_SOURCES.split(",") if s.strip()]

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
