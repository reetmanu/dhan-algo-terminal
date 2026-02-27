from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TradeIntent:
    """Represents a trading signal/intent"""
    def __init__(self, symbol: str, exchange: str, side: str, qty: int,
                 order_type: str = "MARKET", price: float = 0,
                 product: str = "INTRADAY", sl: float = None,
                 target: float = None, security_id: str = "",
                 reason: str = ""):
        self.symbol = symbol
        self.exchange = exchange
        self.side = side  # BUY, SELL, EXIT_BUY, EXIT_SELL
        self.qty = qty
        self.order_type = order_type
        self.price = price
        self.product = product
        self.sl = sl
        self.target = target
        self.security_id = security_id
        self.reason = reason

    def __repr__(self):
        return f"TradeIntent({self.side} {self.qty} {self.symbol} @ {self.order_type})"


class BaseStrategy(ABC):
    """Base class for all trading strategies"""

    name: str = "BaseStrategy"
    description: str = ""
    default_params: Dict[str, Any] = {}

    def __init__(self, config: Dict[str, Any], params: Optional[Dict[str, Any]] = None):
        self.config = config
        self.params = {**self.default_params, **(params or {})}
        self._data_cache: Dict[str, pd.DataFrame] = {}
        logger.info(f"Strategy '{self.name}' initialized with params: {self.params}")

    @abstractmethod
    def on_bar(self, symbol: str, df: pd.DataFrame) -> List[TradeIntent]:
        """
        Called on each new bar/candle.
        Args:
            symbol: Trading symbol
            df: OHLCV DataFrame with columns: open, high, low, close, volume
        Returns:
            List of TradeIntent objects
        """
        raise NotImplementedError

    def calculate_sl_atr(self, df: pd.DataFrame, multiplier: float = 1.5) -> float:
        """Calculate ATR-based stop loss distance"""
        try:
            import pandas_ta as ta
            atr = ta.atr(df['high'], df['low'], df['close'], length=14)
            if atr is not None and len(atr) > 0:
                return float(atr.iloc[-1]) * multiplier
        except Exception:
            pass
        # Fallback: 1% of current price
        return float(df['close'].iloc[-1]) * 0.01

    def get_ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def get_sma(self, series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period).mean()

    def get_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        try:
            import pandas_ta as ta
            return ta.rsi(series, length=period)
        except Exception:
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
