"""Central application configuration via Pydantic Settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_name: str = 'AgentForge'
    app_env: str = 'development'
    secret_key: str = 'change-me'
    debug: bool = False
    allowed_origins: list[str] = ['http://localhost:3000']
    database_url: str = 'postgresql+asyncpg://agentforge:secret@localhost:5432/agentforge'
    redis_url: str = 'redis://localhost:6379/0'
    openai_api_key: str = ''
    anthropic_api_key: str = ''
    openai_default_model: str = 'gpt-4o'
    anthropic_default_model: str = 'claude-3-5-sonnet-20241022'
    chroma_host: str = 'localhost'
    chroma_port: int = 8001
    chroma_collection_prefix: str = 'agentforge_'
    jwt_secret: str = 'change-me-jwt'
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    stripe_secret_key: str = ''
    stripe_webhook_secret: str = ''
    celery_broker_url: str = 'redis://localhost:6379/1'
    celery_result_backend: str = 'redis://localhost:6379/2'

@lru_cache
def get_settings() -> Settings: return Settings()
settings = get_settings()
