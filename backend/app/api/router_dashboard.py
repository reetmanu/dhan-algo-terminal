from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..db.base import get_db
from ..models.order import Order
from ..models.strategy import Strategy
from ..models.config_dhan import ConfigDhan
from pydantic import BaseModel
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class OrderOut(BaseModel):
    id: int
    strategy_id: Optional[int]
    symbol: str
    exchange: str
    order_type: str
    transaction_type: str
    quantity: int
    price: Optional[float]
    status: str
    dhan_order_id: Optional[str]
    created_at: datetime
    is_paper_trade: bool

    class Config:
        from_attributes = True


@router.get("/positions")
def get_positions(db: Session = Depends(get_db)):
    """Get live positions from Dhan API"""
    config = db.query(ConfigDhan).first()
    if not config:
        return {"positions": [], "message": "No config found"}
    if config.paper_trade:
        # Return paper trade positions from orders table
        open_orders = db.query(Order).filter(
            Order.status == "TRADED",
            Order.is_paper_trade == True
        ).all()
        return {"positions": [], "paper_trade": True, "message": "Paper trade mode active"}
    try:
        from ..services.dhan_client import get_dhan_client
        client = get_dhan_client(db)
        positions = client.get_positions()
        return {"positions": positions, "paper_trade": False}
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders", response_model=List[OrderOut])
def get_orders(
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db)
):
    """Get orders history"""
    orders = db.query(Order).order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders


@router.get("/pnl")
def get_pnl(db: Session = Depends(get_db)):
    """Get today's P&L summary"""
    config = db.query(ConfigDhan).first()
    today = date.today()
    today_orders = db.query(Order).filter(
        Order.status == "TRADED"
    ).all()
    total_pnl = sum(o.pnl or 0 for o in today_orders)
    total_trades = len(today_orders)
    winning_trades = sum(1 for o in today_orders if (o.pnl or 0) > 0)
    return {
        "total_pnl": round(total_pnl, 2),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": total_trades - winning_trades,
        "win_rate": round(winning_trades / total_trades * 100, 2) if total_trades > 0 else 0,
        "paper_trade": config.paper_trade if config else True,
        "date": str(today)
    }


@router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    """Get portfolio holdings"""
    config = db.query(ConfigDhan).first()
    if not config or config.paper_trade:
        return {"holdings": [], "paper_trade": True}
    try:
        from ..services.dhan_client import get_dhan_client
        client = get_dhan_client(db)
        holdings = client.get_holdings()
        return {"holdings": holdings, "paper_trade": False}
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/funds")
def get_funds(db: Session = Depends(get_db)):
    """Get available funds"""
    config = db.query(ConfigDhan).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    if config.paper_trade:
        return {"available_balance": 100000, "used_margin": 0, "paper_trade": True}
    try:
        from ..services.dhan_client import get_dhan_client
        client = get_dhan_client(db)
        funds = client.get_fund_limits()
        return {"funds": funds, "paper_trade": False}
    except Exception as e:
        logger.error(f"Error fetching funds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    """Get system status"""
    from ..workers.engine import get_scheduler_status
    config = db.query(ConfigDhan).first()
    active_strategies = db.query(Strategy).filter(Strategy.is_active == True).count()
    total_orders_today = db.query(Order).filter(Order.status == "TRADED").count()
    scheduler_status = get_scheduler_status()
    return {
        "scheduler_running": scheduler_status,
        "active_strategies": active_strategies,
        "orders_today": total_orders_today,
        "config_set": config is not None,
        "paper_trade": config.paper_trade if config else True,
        "connected": config is not None
    }
