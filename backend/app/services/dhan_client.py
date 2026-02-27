from dhanhq import dhanhq
from sqlalchemy.orm import Session
from app.models.order import LogEntry, GlobalSettings
from app.models.config_dhan import ConfigDhan
from datetime import datetime, timezone
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)

_dhan_instance = None


def get_dhan_config_from_db(db: Session) -> ConfigDhan:
    """Get Dhan config from DB (first row)"""
    config = db.query(ConfigDhan).first()
    if not config:
        config = ConfigDhan(id=1, client_id="")
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def get_dhan_instance(db: Session):
    """Get authenticated dhanhq instance"""
    global _dhan_instance
    cfg = get_dhan_config_from_db(db)
    if not cfg.client_id or not cfg.access_token:
        logger.warning("Dhan credentials not configured")
        return None
    try:
        _dhan_instance = dhanhq(cfg.client_id, cfg.access_token)
        return _dhan_instance
    except Exception as e:
        logger.error(f"Error creating Dhan instance: {e}")
        return None


def test_connection(db: Session) -> dict:
    """Test connection by calling get_fund_limits"""
    dhan = get_dhan_instance(db)
    if not dhan:
        return {"success": False, "error": "Dhan not configured"}
    try:
        result = dhan.get_fund_limits()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_fund_limits(db: Session) -> dict:
    dhan = get_dhan_instance(db)
    if not dhan:
        return {}
    try:
        return dhan.get_fund_limits()
    except Exception as e:
        logger.error(f"get_fund_limits error: {e}")
        return {}


def get_positions(db: Session) -> list:
    dhan = get_dhan_instance(db)
    if not dhan:
        return []
    try:
        result = dhan.get_positions()
        if isinstance(result, dict) and "data" in result:
            return result["data"] or []
        return []
    except Exception as e:
        logger.error(f"get_positions error: {e}")
        return []


def get_orders(db: Session) -> list:
    dhan = get_dhan_instance(db)
    if not dhan:
        return []
    try:
        result = dhan.get_order_list()
        if isinstance(result, dict) and "data" in result:
            return result["data"] or []
        return []
    except Exception as e:
        logger.error(f"get_orders error: {e}")
        return []


def place_order(db: Session, symbol: str, exchange: str, side: str, qty: int,
                order_type: str = "MARKET", price: float = 0,
                product: str = "INTRADAY", security_id: str = "",
                sl: float = None, target: float = None) -> dict:
    """Place an order on Dhan"""
    cfg = get_dhan_config_from_db(db)
    if settings.PAPER_TRADING or cfg is None:
        logger.info(f"[PAPER] Would place order: {side} {qty} {symbol} @ {order_type}")
        return {"success": True, "orderId": f"PAPER_{datetime.now().strftime('%Y%m%d%H%M%S')}", "paper": True}

    dhan = get_dhan_instance(db)
    if not dhan:
        return {"success": False, "error": "Dhan not configured"}
    try:
        transaction_type = dhanhq.BUY if side == "BUY" else dhanhq.SELL
        exc = dhanhq.NSE if exchange == "NSE" else dhanhq.BSE
        prod = dhanhq.INTRA if product == "INTRADAY" else dhanhq.CNC
        ot = dhanhq.MARKET if order_type == "MARKET" else dhanhq.LIMIT

        result = dhan.place_order(
            security_id=security_id,
            exchange_segment=exc,
            transaction_type=transaction_type,
            quantity=qty,
            order_type=ot,
            product_type=prod,
            price=price if order_type == "LIMIT" else 0
        )
        log_to_db(db, "INFO", "DHAN", f"Order placed: {side} {qty} {symbol} - {result}")
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"place_order error: {e}")
        log_to_db(db, "ERROR", "DHAN", f"Order error: {e}")
        return {"success": False, "error": str(e)}


def get_intraday_data(db: Session, security_id: str, exchange: str = "NSE",
                      instrument: str = "EQUITY", interval: str = "1") -> list:
    """Get intraday candle data"""
    dhan = get_dhan_instance(db)
    if not dhan:
        return []
    try:
        result = dhan.intraday_minute_charts(
            security_id=security_id,
            exchange_segment=exchange,
            instrument_type=instrument
        )
        if isinstance(result, dict) and "data" in result:
            return result["data"] or []
        return []
    except Exception as e:
        logger.error(f"get_intraday_data error: {e}")
        return []


def log_to_db(db: Session, level: str, source: str, message: str, extra: dict = None):
    """Log event to DB"""
    try:
        entry = LogEntry(
            level=level,
            source=source,
            message=message,
            extra=json.dumps(extra) if extra else None
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.error(f"log_to_db error: {e}")
