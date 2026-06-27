from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(..., alias="BOT_TOKEN")
    database_url: str = Field(..., alias="DATABASE_URL")
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")
    super_admin_id: int = Field(..., alias="SUPER_ADMIN_ID")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Farming settings
    daily_base_reward: int = Field(default=100, alias="DAILY_BASE_REWARD")
    daily_streak_bonus: int = Field(default=50, alias="DAILY_STREAK_BONUS")
    max_streak_days: int = Field(default=30, alias="MAX_STREAK_DAYS")

    # Blacklist cache TTL in seconds
    blacklist_cache_ttl: int = Field(default=300, alias="BLACKLIST_CACHE_TTL")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            # Handle comma-separated string: "1,2,3" -> [1, 2, 3]
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, list):
            return v
        return []


settings = Settings()