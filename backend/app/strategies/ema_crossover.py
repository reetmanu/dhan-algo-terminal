import pandas as pd
from typing import List, Dict, Any
from app.strategies.base import BaseStrategy, TradeIntent
import logging

logger = logging.getLogger(__name__)


class EMACrossoverStrategy(BaseStrategy):
    """
    EMA Crossover Strategy with RSI filter.
    BUY when fast EMA crosses above slow EMA and RSI > 50.
    SELL when fast EMA crosses below slow EMA and RSI < 50.
    """
    name = "ema_crossover"
    description = "EMA Crossover with RSI filter - intraday NSE/BSE stocks"
    default_params = {
        "ema_fast": 9,
        "ema_slow": 21,
        "rsi_period": 14,
        "rsi_buy_threshold": 55,
        "rsi_sell_threshold": 45,
        "sl_pct": 1.0,
        "target_pct": 2.0,
        "qty": 1,
        "product": "INTRADAY"
    }

    def __init__(self, config: Dict[str, Any], params: Dict[str, Any] = None):
        super().__init__(config, params)
        self._positions: Dict[str, str] = {}  # symbol -> side

    def on_bar(self, symbol: str, df: pd.DataFrame) -> List[TradeIntent]:
        intents = []
        try:
            if len(df) < self.params['ema_slow'] + 5:
                return intents

            close = df['close']
            fast_ema = self.get_ema(close, self.params['ema_fast'])
            slow_ema = self.get_ema(close, self.params['ema_slow'])
            rsi = self.get_rsi(close, self.params['rsi_period'])

            if fast_ema.isna().iloc[-1] or slow_ema.isna().iloc[-1]:
                return intents

            prev_fast = fast_ema.iloc[-2]
            prev_slow = slow_ema.iloc[-2]
            curr_fast = fast_ema.iloc[-1]
            curr_slow = slow_ema.iloc[-1]
            curr_rsi = rsi.iloc[-1] if rsi is not None and not rsi.isna().iloc[-1] else 50
            curr_price = float(close.iloc[-1])

            symbol_position = self._positions.get(symbol)
            exchange = self.config.get('exchange', 'NSE')
            security_id = self.config.get('security_id', '')
            qty = int(self.params.get('qty', 1))
            product = self.params.get('product', 'INTRADAY')

            sl_pct = self.params.get('sl_pct', 1.0) / 100
            target_pct = self.params.get('target_pct', 2.0) / 100

            # Bullish crossover: fast EMA crosses above slow EMA
            bullish_cross = prev_fast <= prev_slow and curr_fast > curr_slow
            # Bearish crossover: fast EMA crosses below slow EMA
            bearish_cross = prev_fast >= prev_slow and curr_fast < curr_slow

            if bullish_cross and curr_rsi >= self.params['rsi_buy_threshold']:
                if symbol_position != 'BUY':
                    # Exit short if any
                    if symbol_position == 'SELL':
                        intents.append(TradeIntent(
                            symbol=symbol, exchange=exchange, side='BUY',
                            qty=qty, order_type='MARKET', product=product,
                            security_id=security_id, reason='Exit Short + EMA Cross'
                        ))
                    sl = curr_price * (1 - sl_pct)
                    target = curr_price * (1 + target_pct)
                    intents.append(TradeIntent(
                        symbol=symbol, exchange=exchange, side='BUY',
                        qty=qty, order_type='MARKET', product=product,
                        sl=sl, target=target, security_id=security_id,
                        reason=f'EMA Cross BUY: fast={curr_fast:.2f} slow={curr_slow:.2f} rsi={curr_rsi:.1f}'
                    ))
                    self._positions[symbol] = 'BUY'
                    logger.info(f"BUY signal: {symbol} @ {curr_price:.2f}")

            elif bearish_cross and curr_rsi <= self.params['rsi_sell_threshold']:
                if symbol_position != 'SELL':
                    # Exit long if any
                    if symbol_position == 'BUY':
                        intents.append(TradeIntent(
                            symbol=symbol, exchange=exchange, side='SELL',
                            qty=qty, order_type='MARKET', product=product,
                            security_id=security_id, reason='Exit Long + EMA Cross'
                        ))
                    sl = curr_price * (1 + sl_pct)
                    target = curr_price * (1 - target_pct)
                    intents.append(TradeIntent(
                        symbol=symbol, exchange=exchange, side='SELL',
                        qty=qty, order_type='MARKET', product=product,
                        sl=sl, target=target, security_id=security_id,
                        reason=f'EMA Cross SELL: fast={curr_fast:.2f} slow={curr_slow:.2f} rsi={curr_rsi:.1f}'
                    ))
                    self._positions[symbol] = 'SELL'
                    logger.info(f"SELL signal: {symbol} @ {curr_price:.2f}")

        except Exception as e:
            logger.error(f"EMACrossover.on_bar error for {symbol}: {e}")

        return intents
