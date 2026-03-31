from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    project_name: str = "RAG Service"
    redis_url: str = "redis://redis:6379/0"
    database_url: str

    # MinIO / S3
    minio_endpoint: str
    minio_root_user: str
    minio_root_password: str
    minio_bucket_name: str

    llm_model_name: str = "gpt-4o-mini"
    embedding_model_name: str = "text-embedding-3-small"   
    openai_api_key: SecretStr
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()