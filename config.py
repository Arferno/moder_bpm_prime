from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
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
    admin_ids_str: str = Field(default="", alias="ADMIN_IDS")
    super_admin_id: int = Field(..., alias="SUPER_ADMIN_ID")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Farming settings
    daily_base_reward: int = Field(default=100, alias="DAILY_BASE_REWARD")
    daily_streak_bonus: int = Field(default=50, alias="DAILY_STREAK_BONUS")
    max_streak_days: int = Field(default=30, alias="MAX_STREAK_DAYS")

    # Blacklist cache TTL in seconds
    blacklist_cache_ttl: int = Field(default=300, alias="BLACKLIST_CACHE_TTL")

    @property
    def admin_ids(self) -> List[int]:
        if not self.admin_ids_str:
            return []
        return [int(x.strip()) for x in self.admin_ids_str.split(",") if x.strip()]


settings = Settings()