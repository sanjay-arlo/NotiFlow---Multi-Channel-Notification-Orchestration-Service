"""
Core configuration settings using Pydantic Settings.
"""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # App
    app_name: str = Field(default="NotiFlow", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    secret_key: str = Field(description="Secret key for security")
    
    # Database
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="notiflow", description="Database name")
    db_user: str = Field(default="notiflow", description="Database user")
    db_password: str = Field(description="Database password")
    db_pool_size: int = Field(default=20, description="Database pool size")
    db_max_overflow: int = Field(default=10, description="Database max overflow")
    
    @property
    def database_url(self) -> str:
        """Get the database URL."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    # Redis
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_max_connections: int = Field(default=50, description="Redis max connections")
    
    @property
    def redis_url(self) -> str:
        """Get the Redis URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Celery
    celery_broker_url: Optional[str] = Field(default=None, description="Celery broker URL")
    celery_result_backend: Optional[str] = Field(default=None, description="Celery result backend")
    
    @validator("celery_broker_url", pre=True, always=True)
    def set_celery_broker_url(cls, v, values):
        """Set default Celery broker URL from Redis."""
        if v is None and "redis_host" in values:
            redis_host = values["redis_host"]
            redis_port = values["redis_port"]
            redis_password = values.get("redis_password")
            auth = f":{redis_password}@" if redis_password else ""
            return f"redis://{auth}{redis_host}:{redis_port}/0"
        return v
    
    @validator("celery_result_backend", pre=True, always=True)
    def set_celery_result_backend(cls, v, values):
        """Set default Celery result backend from Redis."""
        if v is None and "redis_host" in values:
            redis_host = values["redis_host"]
            redis_port = values["redis_port"]
            redis_password = values.get("redis_password")
            auth = f":{redis_password}@" if redis_password else ""
            return f"redis://{auth}{redis_host}:{redis_port}/1"
        return v
    
    # Email (SMTP)
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_user: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_from_email: Optional[str] = Field(default=None, description="From email address")
    smtp_from_name: str = Field(default="NotiFlow", description="From name")
    smtp_use_tls: bool = Field(default=True, description="Use TLS for SMTP")
    smtp_timeout: int = Field(default=30, description="SMTP timeout in seconds")
    
    # SMS (Twilio)
    twilio_account_sid: Optional[str] = Field(default=None, description="Twilio account SID")
    twilio_auth_token: Optional[str] = Field(default=None, description="Twilio auth token")
    twilio_from_number: Optional[str] = Field(default=None, description="Twilio from number")
    twilio_timeout: int = Field(default=30, description="Twilio timeout in seconds")
    
    # Webhook
    webhook_default_timeout: int = Field(default=10, description="Default webhook timeout")
    webhook_signature_algorithm: str = Field(default="sha256", description="Webhook signature algorithm")
    
    # Retry Defaults
    default_max_retries: int = Field(default=3, description="Default max retries")
    default_base_delay_seconds: int = Field(default=60, description="Default base delay")
    default_max_delay_seconds: int = Field(default=3600, description="Default max delay")
    
    # Quiet Hours
    default_quiet_hours_enabled: bool = Field(default=False, description="Default quiet hours enabled")
    
    # Rate Limiting
    default_tenant_rate_limit: int = Field(default=1000, description="Default tenant rate limit")
    default_tenant_rate_window: int = Field(default=60, description="Default tenant rate window")
    
    # Templates
    template_dir: str = Field(default="templates/", description="Template directory")
    
    # Flower (Celery Monitor)
    flower_port: int = Field(default=5555, description="Flower port")
    flower_url_prefix: str = Field(default="flower", description="Flower URL prefix")
    
    # API
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
