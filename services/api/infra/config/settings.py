from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, List, Sequence

from pydantic import AnyUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Глобальные настройки API сервиса, загружаемые из env переменных."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = Field(default="local", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=9090, alias="API_PORT")

    postgres_dsn: PostgresDsn = Field(alias="POSTGRES_DSN")
    db_echo: bool = Field(default=False, alias="DB_ECHO")
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    redis_url: AnyUrl = Field(alias="REDIS_URL")

    celery_broker_url: AnyUrl | None = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: AnyUrl | None = Field(default=None, alias="CELERY_RESULT_BACKEND")
    celery_timezone: str = Field(default="UTC", alias="CELERY_TIMEZONE")
    celery_task_default_queue: str = Field(default="nbo_default", alias="CELERY_DEFAULT_QUEUE")
    celery_imports: Sequence[str] = Field(
        default=("services.workers.tasks",),
        alias="CELERY_IMPORTS",
    )

    feast_repo_path: Path = Field(default=Path("/opt/feast_repo"), alias="FEAST_REPO_PATH")
    model_registry_path: Path = Field(default=Path("/opt/models"), alias="MODEL_REGISTRY_PATH")
    als_factors: int = Field(default=64, alias="ALS_FACTORS")
    als_reg: float = Field(default=0.1, alias="ALS_REG")
    lgbm_model_path: Path = Field(default=Path("/opt/models/lgbm.bin"), alias="LGBM_MODEL_PATH")

    nbo_retry_window_seconds: int = Field(default=30, alias="NBO_RETRY_WINDOW_SECONDS")
    event_idempotency_window_seconds: int = Field(
        default=600, alias="EVENT_IDEMPOTENCY_WINDOW_SECONDS"
    )
    ab_variants: List[str] = Field(
        default_factory=lambda: ["control", "treatmentA"],
        alias="AB_VARIANTS",
    )

    tracing_endpoint: AnyUrl | None = Field(default=None, alias="TRACING_ENDPOINT")
    metrics_port: int = Field(default=9091, alias="METRICS_PORT")

    @field_validator("ab_variants", mode="before")
    @classmethod
    def _split_variants(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [variant.strip() for variant in value.split(",") if variant.strip()]
        if value is None:
            return ["control", "treatmentA"]
        return list(value)

    @field_validator("celery_imports", mode="before")
    @classmethod
    def _ensure_sequence(cls, value: Any) -> Sequence[str]:
        if value is None:
            return ("services.workers.tasks",)
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split(",") if part.strip())
        return value

    @property
    def celery_broker(self) -> str:
        return str(self.celery_broker_url or self.redis_url)

    @property
    def celery_backend(self) -> str:
        return str(self.celery_result_backend or self.redis_url)


@lru_cache
def get_settings() -> Settings:
    """Возвращает singleton экземпляр настроек."""

    return Settings()


