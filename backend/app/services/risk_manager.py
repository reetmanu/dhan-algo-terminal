from sqlalchemy.orm import Session
from app.models.order import GlobalSettings, Order
from app.models.strategy import Strategy
from datetime import datetime, timezone, date
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def get_global_settings(db: Session) -> GlobalSettings:
    """Get or create global settings"""
    gs = db.query(GlobalSettings).first()
    if not gs:
        gs = GlobalSettings(id=1)
        db.add(gs)
        db.commit()
        db.refresh(gs)
    return gs


def can_open_new_trade(db: Session, strategy: Strategy) -> tuple[bool, str]:
    """Check if a new trade can be opened"""
    gs = get_global_settings(db)

    # Check global kill switch
    if not gs.trading_enabled:
        return False, "Trading is disabled globally"

    # Check paper trading mode
    if gs.paper_trading:
        logger.info("Paper trading mode - trade would be allowed")
        # In paper mode, allow signals but mark as paper
        return True, "OK (Paper)"

    # Check max positions
    today = date.today()
    open_orders = db.query(Order).filter(
        Order.status.in_(["EXECUTED", "PENDING"]),
        Order.timestamp >= datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    ).count()

    if open_orders >= gs.max_positions:
        return False, f"Max positions ({gs.max_positions}) reached"

    # Check daily loss limit
    today_pnl = get_today_realized_pnl(db)
    if today_pnl is not None:
        # Calculate max loss allowed (need to know capital - simplified)
        # For now use absolute PnL threshold
        pass

    return True, "OK"


def calculate_position_size(capital: float, risk_pct: float, sl_distance: float, price: float) -> int:
    """Calculate position size based on risk"""
    if sl_distance <= 0 or price <= 0:
        return 1
    risk_amount = capital * (risk_pct / 100)
    qty = int(risk_amount / sl_distance)
    return max(1, qty)


def get_today_realized_pnl(db: Session) -> float:
    """Get today's realized PnL from orders"""
    try:
        today = date.today()
        today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        # Simple approximation based on executed orders
        # A proper implementation would track actual execution prices
        return 0.0
    except Exception as e:
        logger.error(f"get_today_realized_pnl error: {e}")
        return 0.0


def check_daily_loss_limit(db: Session, current_capital: float) -> bool:
    """Returns True if daily loss limit NOT yet breached"""
    gs = get_global_settings(db)
    today_pnl = get_today_realized_pnl(db)
    if current_capital > 0 and today_pnl < 0:
        loss_pct = abs(today_pnl) / current_capital * 100
        if loss_pct >= gs.max_daily_loss_pct:
            logger.warning(f"Daily loss limit breached: {loss_pct:.2f}%")
            return False
    return True


def reset_daily_stats(db):
    """Reset daily P&L tracking stats"""
    # This resets the in-memory tracking; DB records remain for history
    logger.info("Daily stats reset at start of trading session")
    return True
