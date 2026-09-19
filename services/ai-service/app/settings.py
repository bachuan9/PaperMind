from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ai_data_dir: Path = Path("./data")
    ai_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    ai_max_upload_mb: int = 25
    ai_parse_max_attempts: int = 2
    ai_queue_backend: str = "inline"
    ai_redis_url: str = "redis://localhost:6379/0"
    ai_redis_queue_name: str = "papermind:document-processing"
    ai_queue_poll_timeout_seconds: int = 5
    ai_rate_limit_per_minute: int = 120
    ai_request_log_enabled: bool = True
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.siliconflow.cn/v1"
    llm_model: str = "deepseek-ai/DeepSeek-V4-Flash"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2
    llm_input_price_per_1m_tokens: float = 0.0
    llm_output_price_per_1m_tokens: float = 0.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ai_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
