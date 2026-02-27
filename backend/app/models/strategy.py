from sqlalchemy import Column, Integer, String, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    module_name = Column(String(100), nullable=False)
    class_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    timeframe = Column(String(10), default="1min")
    is_enabled = Column(Boolean, default=False)
    params = Column(JSON, default={})

    watchlist_items = relationship("WatchlistItem", back_populates="strategy", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="strategy")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, nullable=False)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(10), default="NSE")  # NSE or BSE
    security_id = Column(String(50), nullable=True)  # Dhan security ID

    strategy = relationship("Strategy", back_populates="watchlist_items")
