from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.base import get_db
from ..models.strategy import Strategy
from ..models.order import Order
from ..models.config_dhan import ConfigDhan
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/control", tags=["control"])


@router.post("/kill-switch")
def kill_switch(db: Session = Depends(get_db)):
    """Emergency kill switch - stop all strategies and scheduler"""
    from ..workers.engine import stop_scheduler
    # Deactivate all strategies
    db.query(Strategy).update({Strategy.is_active: False})
    db.commit()
    # Stop scheduler
    stop_scheduler()
    logger.warning("KILL SWITCH ACTIVATED - All strategies stopped")
    return {
        "status": "success",
        "message": "Kill switch activated. All strategies stopped and scheduler halted."
    }


@router.post("/start-scheduler")
def start_scheduler_endpoint(db: Session = Depends(get_db)):
    """Start the strategy scheduler"""
    from ..workers.engine import start_scheduler, get_scheduler_status
    config = db.query(ConfigDhan).first()
    if not config:
        raise HTTPException(status_code=400, detail="Please configure Dhan API credentials first")
    if get_scheduler_status():
        return {"status": "already_running", "message": "Scheduler is already running"}
    start_scheduler(db)
    logger.info("Scheduler started via API")
    return {"status": "started", "message": "Strategy scheduler started"}


@router.post("/stop-scheduler")
def stop_scheduler_endpoint():
    """Stop the strategy scheduler"""
    from ..workers.engine import stop_scheduler, get_scheduler_status
    if not get_scheduler_status():
        return {"status": "not_running", "message": "Scheduler is not running"}
    stop_scheduler()
    logger.info("Scheduler stopped via API")
    return {"status": "stopped", "message": "Strategy scheduler stopped"}


@router.get("/scheduler-status")
def scheduler_status():
    """Get scheduler running status"""
    from ..workers.engine import get_scheduler_status
    running = get_scheduler_status()
    return {"running": running, "status": "running" if running else "stopped"}


@router.post("/reset-daily-pnl")
def reset_daily_pnl(db: Session = Depends(get_db)):
    """Reset daily P&L tracking (use at start of trading day)"""
    from ..services.risk_manager import reset_daily_stats
    reset_daily_stats(db)
    logger.info("Daily P&L reset")
    return {"status": "success", "message": "Daily P&L stats reset"}


@router.post("/toggle-paper-trade")
def toggle_paper_trade(db: Session = Depends(get_db)):
    """Toggle paper trade mode on/off"""
    config = db.query(ConfigDhan).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    config.paper_trade = not config.paper_trade
    db.commit()
    mode = "Paper Trading" if config.paper_trade else "Live Trading"
    logger.warning(f"Trading mode changed to: {mode}")
    return {
        "paper_trade": config.paper_trade,
        "mode": mode,
        "message": f"Switched to {mode} mode"
    }


class RiskSettings(BaseModel):
    max_daily_loss_pct: Optional[float] = None
    max_positions: Optional[int] = None


@router.put("/risk-settings")
def update_risk_settings(settings: RiskSettings, db: Session = Depends(get_db)):
    """Update risk management settings"""
    config = db.query(ConfigDhan).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    if settings.max_daily_loss_pct is not None:
        config.max_daily_loss_pct = settings.max_daily_loss_pct
    if settings.max_positions is not None:
        config.max_positions = settings.max_positions
    db.commit()
    logger.info(f"Risk settings updated: {settings.dict(exclude_none=True)}")
    return {
        "max_daily_loss_pct": config.max_daily_loss_pct,
        "max_positions": config.max_positions,
        "message": "Risk settings updated"
    }
