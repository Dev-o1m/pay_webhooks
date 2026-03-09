from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Pay Webhooks'
    app_host: str = '0.0.0.0'
    app_port: int = 8000
    database_url: str = Field(
        default='postgresql+asyncpg://pay_user:pay_password@postgres:5432/payments'
    )
    alembic_database_url: str = Field(
        default='postgresql://pay_user:pay_password@postgres:5432/payments'
    )
    redis_url: str = 'redis://redis:6379/0'
    provider_base_url: str = 'http://app:8000/provider'
    public_base_url: str = 'http://app:8000'
    provider_webhook_secret: str = 'provider-webhook-secret'
    request_delay_min_seconds: float = 1.0
    request_delay_max_seconds: float = 2.0
    provider_decision_delay_seconds: float = 0.2
    testing: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
