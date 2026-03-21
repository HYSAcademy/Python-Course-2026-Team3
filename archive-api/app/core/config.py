from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str
    database_url_pgbouncer: str
    redis_url: str = "redis://redis:6379/0"

    # MinIO / S3
    minio_endpoint: str
    minio_root_user: str
    minio_root_password: str
    minio_bucket_name: str

    # App limits
    max_upload_size_mb: int = 50
    max_extract_size_mb: int = 200

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
