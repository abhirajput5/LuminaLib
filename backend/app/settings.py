# app/settings.py
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="dev")
    storage_provider: str = Field(
        description="Storage provider to use (e.g. 'minio', 'local')"
    )
    llm_provider: str = Field(
        description="LLM provider to use (e.g. 'ollama', 'openai')"
    )

    # Database Config
    db_url: str = Field(..., description="PostgreSQL connection URL")
    db_min_pool_size: int = 1
    db_max_pool_size: int = 10

    # Storage Config
    minio_endpoint: str = Field(description="MinIO server endpoint")
    minio_access_key: str = Field(default="minioadmin", description="MinIO access key")
    minio_secret_key: str = Field(
        default="minioadmin123", description="MinIO secret key"
    )
    minio_bucket: str = Field(default="lumina", description="MinIO bucket name")
    s3_bucket: str = Field(default="lumina", description="S3 bucket name")
    s3_region: str = Field(default="us-east-1", description="AWS S3 region")
    s3_access_key: str = Field(default="", description="AWS S3 access key")
    s3_secret_key: str = Field(default="", description="AWS S3 secret key")
    celery_broker_url: str = Field(description="Celery broker URL")
    celery_result_backend: str = Field(description="Celery result backend URL")

    # LLM Config
    ollama_api_base: str = Field(description="Ollama API base URL")
    ollama_model_name: str = Field(description="Ollama model name")
    openai_api_key: str = Field(description="OpenAI API key")
    openai_api_base: str = Field(description="OpenAI API base URL")
    openai_model_name: str = Field(description="OpenAI model name")

    #
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton instance
settings = Settings()  # type: ignore
