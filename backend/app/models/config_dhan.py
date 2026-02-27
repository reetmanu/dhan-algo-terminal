from sqlalchemy import Column, Integer, String, DateTime
from app.db.base import Base
from datetime import datetime, timezone


class ConfigDhan(Base):
    __tablename__ = "config_dhan"

    id = Column(Integer, primary_key=True, index=True, default=1)
    client_id = Column(String, nullable=False, default="")
    api_key = Column(String, nullable=True)
    api_secret = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
