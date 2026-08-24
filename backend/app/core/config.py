from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL async connection string")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection string")
    
    # MinIO
    MINIO_ENDPOINT: str = Field(default="localhost:9000", description="MinIO endpoint")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin", description="MinIO access key")
    MINIO_SECRET_KEY: str = Field(default="minioadmin", description="MinIO secret key")
    MINIO_BUCKET: str = Field(default="civicops", description="MinIO bucket name")
    MINIO_SECURE: bool = Field(default=False, description="Use HTTPS for MinIO")
    
    # NVIDIA
    NVIDIA_API_KEY: str = Field(..., description="NVIDIA API key for Nemotron/Llama models")
    
    # Langfuse
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(default=None, description="Langfuse public key")
    LANGFUSE_SECRET_KEY: Optional[str] = Field(default=None, description="Langfuse secret key")
    LANGFUSE_HOST: str = Field(default="https://cloud.langfuse.com", description="Langfuse host")
    
    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(default="http://localhost:4317", description="OTLP endpoint")
    OTEL_SERVICE_NAME: str = Field(default="civicops-api", description="Service name for tracing")
    
    # App
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    
    # Confidence thresholds
    CONFIDENCE_THRESHOLD_AUTO: float = Field(default=0.9, description="Auto-process threshold")
    CONFIDENCE_THRESHOLD_REVIEW: float = Field(default=0.7, description="Mandatory review threshold")
    
    # Models
    WHISPER_MODEL: str = Field(default="base", description="Whisper model size")
    VISION_MODEL: str = Field(default="google/vit-base-patch16-224", description="Vision model")
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Embedding model")
    NVIDIA_MODEL: str = Field(default="nvidia/nemotron-3-ultra-550b-a55b", description="NVIDIA LLM model")
    NVIDIA_BASE_URL: str = Field(default="https://integrate.api.nvidia.com/v1", description="NVIDIA API base URL")
    
    # External APIs
    GOOGLE_MAPS_API_KEY: Optional[str] = Field(default=None, description="Google Maps API key")
    WEATHER_API_KEY: Optional[str] = Field(default=None, description="Weather API key")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()