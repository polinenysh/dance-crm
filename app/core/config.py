from functools import lru_cache
from datetime import datetime

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from zoneinfo import ZoneInfo

MOSCOW_TIMEZONE = ZoneInfo("Europe/Moscow")

def to_moscow_time(value: datetime) -> datetime:
    """Преобразует дату и время в московский часовой пояс."""
    return value.astimezone(MOSCOW_TIMEZONE)

class Settings(BaseSettings):
    app_name: str = "Dance CRM API"
    app_version: str = "0.1.0"
    debug: bool = False

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int = 5432

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    log_level: str = "INFO"
    log_sql: bool = False
    log_file: str = "logs/app.log"
    audit_log_file: str = "logs/audit.log"
    log_max_bytes: int = 10_485_760
    log_backup_count: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.postgres_user}:"
            f"{self.postgres_password}@"
            f"{self.postgres_host}:"
            f"{self.postgres_port}/"
            f"{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()