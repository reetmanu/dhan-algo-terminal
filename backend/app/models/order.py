from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime, timezone


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(10), default="NSE")
    side = Column(String(10), nullable=False)  # BUY or SELL
    qty = Column(Integer, nullable=False)
    price = Column(Float, nullable=True)
    order_type = Column(String(20), default="MARKET")  # MARKET, LIMIT
    product = Column(String(20), default="INTRADAY")  # INTRADAY, CNC
    sl = Column(Float, nullable=True)
    target = Column(Float, nullable=True)
    status = Column(String(20), default="PENDING")  # PENDING, EXECUTED, CANCELLED, REJECTED
    dhan_order_id = Column(String(100), nullable=True)
    algo_order_id = Column(String(100), nullable=True)
    is_paper = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    strategy = relationship("Strategy", back_populates="orders")


class LogEntry(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    level = Column(String(10), default="INFO")  # INFO, WARN, ERROR
    source = Column(String(50), default="ENGINE")  # ENGINE, API, STRATEGY, DHAN
    message = Column(Text, nullable=False)
    extra = Column(Text, nullable=True)  # JSON string for extra data


class GlobalSettings(Base):
    __tablename__ = "global_settings"

    id = Column(Integer, primary_key=True, default=1)
    trading_enabled = Column(Boolean, default=False)
    max_daily_loss_pct = Column(Float, default=2.0)
    max_positions = Column(Integer, default=3)
    max_capital_per_trade_pct = Column(Float, default=10.0)
    paper_trading = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class EquityCurve(Base):
    __tablename__ = "equity_curve"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    equity_value = Column(Float, nullable=True)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
