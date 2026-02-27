from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://dhan:dhanpass@localhost:5432/dhanalgo"

    # App
    APP_SECRET_KEY: str = "change-this-secret-key-in-production"
    DEBUG: bool = False

    # Market hours (IST = UTC+5:30)
    MARKET_OPEN_HOUR: int = 9
    MARKET_OPEN_MINUTE: int = 15
    MARKET_CLOSE_HOUR: int = 15
    MARKET_CLOSE_MINUTE: int = 30
    TIMEZONE: str = "Asia/Kolkata"

    # Telegram alerts (optional)
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Paper trading mode
    PAPER_TRADING: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


settings = Settings()
