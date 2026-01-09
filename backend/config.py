"""
Application configuration using Pydantic Settings.
Environment variables are loaded from .env file.
"""
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # API Configuration
    fastapi_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_root_path: str = "/api/v1"

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "va_scheduler"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection string."""
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis / Celery
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # OpenAI / LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    openai_temperature: float = 0.7

    # Gmail OAuth2
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = "http://localhost:8000/api/v1/auth/gmail/callback"
    gmail_scopes: str = "https://www.googleapis.com/auth/gmail.modify"

    # Outlook OAuth2
    outlook_client_id: str = ""
    outlook_client_secret: str = ""
    outlook_redirect_uri: str = "http://localhost:8000/api/v1/auth/outlook/callback"

    # Encryption
    encryption_key: str = ""  # Fernet key for token encryption
    secret_key: str = "dev-secret-key-change-in-production"

    # AWS / S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = "va-scheduler"
    aws_s3_region: str = "nyc3"
    aws_s3_endpoint_url: str = "https://nyc3.digitaloceanspaces.com"

    # Sentry
    sentry_dsn: Optional[str] = None
    sentry_environment: str = "development"

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
