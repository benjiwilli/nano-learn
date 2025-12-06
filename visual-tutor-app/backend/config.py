"""Configuration management for Visual Tutor App."""

import os
from typing import Optional
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


def load_genspark_config():
    """Load GenSpark configuration from ~/.genspark_llm.yaml if available."""
    config_path = Path.home() / ".genspark_llm.yaml"
    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)
                return config.get("openai", {})
        except Exception:
            pass
    return {}


# Try to load from config file
_genspark_config = load_genspark_config()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys - Try multiple sources
    gemini_api_key: str = Field(
        default=os.environ.get("OPENAI_API_KEY", "") or _genspark_config.get("api_key", ""),
        env="GEMINI_API_KEY"
    )
    genspark_api_key: str = Field(
        default=os.environ.get("OPENAI_API_KEY", "") or _genspark_config.get("api_key", ""),
        env="GENSPARK_API_KEY"
    )
    openai_api_key: str = Field(
        default=os.environ.get("OPENAI_API_KEY", "") or _genspark_config.get("api_key", ""),
        env="OPENAI_API_KEY"
    )

    # API URLs
    genspark_base_url: str = Field(
        default=os.environ.get("OPENAI_BASE_URL", "") or _genspark_config.get("base_url", "https://www.genspark.ai/api/llm_proxy/v1"),
        env="GENSPARK_BASE_URL"
    )
    openai_base_url: str = Field(
        default=os.environ.get("OPENAI_BASE_URL", "") or _genspark_config.get("base_url", "https://www.genspark.ai/api/llm_proxy/v1"),
        env="OPENAI_BASE_URL"
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000", env="CORS_ORIGINS"
    )

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, env="RATE_LIMIT_WINDOW_SECONDS")

    # Image Processing
    max_image_size_mb: int = Field(default=10, env="MAX_IMAGE_SIZE_MB")
    image_compression_quality: int = Field(default=85, env="IMAGE_COMPRESSION_QUALITY")

    # Caching
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")

    # Generation Settings
    image_generation_timeout_seconds: int = Field(default=60)
    gemini_timeout_seconds: int = Field(default=30)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Singleton instance for easy import
settings = get_settings()
