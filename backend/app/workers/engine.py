from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.db.base import SessionLocal
from app.models.strategy import Strategy, WatchlistItem
from app.models.order import Order, LogEntry, GlobalSettings
from app.strategies.registry import get_strategy_class
from app.services import dhan_client, risk_manager
from app.core.config import settings
from datetime import datetime
import pytz
import pandas as pd
import logging
import json

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler()
_strategy_instances = {}
_is_market_open = False


def is_market_open() -> bool:
    """Check if Indian stock market is open"""
    ist = pytz.timezone(settings.TIMEZONE)
    now = datetime.now(ist)
    # Market is closed on weekends
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    market_open = now.replace(
        hour=settings.MARKET_OPEN_HOUR,
        minute=settings.MARKET_OPEN_MINUTE,
        second=0, microsecond=0
    )
    market_close = now.replace(
        hour=settings.MARKET_CLOSE_HOUR,
        minute=settings.MARKET_CLOSE_MINUTE,
        second=0, microsecond=0
    )
    return market_open <= now <= market_close


def get_or_create_strategy_instance(strategy: Strategy):
    """Get or create strategy instance from registry"""
    global _strategy_instances
    if strategy.id not in _strategy_instances:
        cls = get_strategy_class(strategy.module_name)
        if cls is None:
            logger.error(f"Strategy class not found: {strategy.module_name}")
            return None
        config = {"product": "INTRADAY"}
        params = strategy.params or {}
        _strategy_instances[strategy.id] = cls(config=config, params=params)
    return _strategy_instances[strategy.id]


def candles_to_df(candle_data: list) -> pd.DataFrame:
    """Convert Dhan candle data to DataFrame"""
    if not candle_data:
        return pd.DataFrame()
    try:
        df = pd.DataFrame(candle_data)
        # Dhan returns: open, high, low, close, volume, timestamp
        col_map = {
            'open': 'open', 'high': 'high', 'low': 'low',
            'close': 'close', 'volume': 'volume'
        }
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        logger.error(f"candles_to_df error: {e}")
        return pd.DataFrame()


def run_strategy_cycle():
    """Main strategy execution cycle - runs every minute"""
    if not is_market_open():
        return

    db = SessionLocal()
    try:
        gs = db.query(GlobalSettings).first()
        if not gs or not gs.trading_enabled:
            if gs and not gs.trading_enabled:
                pass  # Trading disabled, skip
            return

        active_strategies = db.query(Strategy).filter(Strategy.is_enabled == True).all()
        if not active_strategies:
            return

        logger.info(f"Running {len(active_strategies)} active strategies")

        for strategy in active_strategies:
            try:
                watchlist = db.query(WatchlistItem).filter(
                    WatchlistItem.strategy_id == strategy.id
                ).all()

                if not watchlist:
                    continue

                strategy_instance = get_or_create_strategy_instance(strategy)
                if not strategy_instance:
                    continue

                for item in watchlist:
                    try:
                        # Fetch intraday data
                        candles = dhan_client.get_intraday_data(
                            db=db,
                            security_id=item.security_id or item.symbol,
                            exchange=item.exchange
                        )

                        if not candles:
                            continue

                        df = candles_to_df(candles)
                        if df.empty or len(df) < 5:
                            continue

                        # Run strategy
                        config = {
                            'exchange': item.exchange,
                            'security_id': item.security_id or '',
                            'product': strategy.params.get('product', 'INTRADAY') if strategy.params else 'INTRADAY'
                        }
                        strategy_instance.config = config

                        intents = strategy_instance.on_bar(item.symbol, df)

                        for intent in intents:
                            # Check risk
                            can_trade, reason = risk_manager.can_open_new_trade(db, strategy)
                            if not can_trade:
                                logger.info(f"Trade blocked for {item.symbol}: {reason}")
                                continue

                            # Place order
                            result = dhan_client.place_order(
                                db=db,
                                symbol=intent.symbol,
                                exchange=intent.exchange,
                                side=intent.side,
                                qty=intent.qty,
                                order_type=intent.order_type,
                                price=intent.price,
                                product=intent.product,
                                security_id=intent.security_id,
                                sl=intent.sl,
                                target=intent.target
                            )

                            # Log to DB
                            is_paper = gs.paper_trading
                            order_entry = Order(
                                strategy_id=strategy.id,
                                symbol=intent.symbol,
                                exchange=intent.exchange,
                                side=intent.side,
                                qty=intent.qty,
                                order_type=intent.order_type,
                                product=intent.product,
                                sl=intent.sl,
                                target=intent.target,
                                is_paper=is_paper,
                                status="PAPER" if is_paper else "EXECUTED",
                                dhan_order_id=result.get('orderId') if result.get('success') else None,
                                notes=intent.reason
                            )
                            db.add(order_entry)
                            db.commit()

                            logger.info(f"{'[PAPER]' if is_paper else '[LIVE]'} {intent.side} {intent.qty} {intent.symbol}: {intent.reason}")

                    except Exception as e:
                        logger.error(f"Error processing {item.symbol} for strategy {strategy.name}: {e}")

            except Exception as e:
                logger.error(f"Error running strategy {strategy.name}: {e}")

    except Exception as e:
        logger.error(f"run_strategy_cycle error: {e}")
    finally:
        db.close()


def start_scheduler():
    """Start the APScheduler"""
    global _scheduler
    if not _scheduler.running:
        # Run strategy cycle every minute at :05 seconds
        _scheduler.add_job(
            run_strategy_cycle,
            CronTrigger(second=5),  # Every minute at :05
            id='strategy_cycle',
            replace_existing=True
        )
        _scheduler.start()
        logger.info("Strategy scheduler started")


def stop_scheduler():
    """Stop the scheduler"""
    global _scheduler
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Strategy scheduler stopped")


def get_scheduler_status() -> bool:
    """Get current scheduler running status"""
    global _scheduler
    return _scheduler.running if _scheduler else False
