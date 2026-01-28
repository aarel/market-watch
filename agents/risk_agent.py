"""Risk Agent - validates trades before execution."""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import TYPE_CHECKING

from risk.position_sizer import PositionSizer
from risk.circuit_breaker import CircuitBreaker

from .base import BaseAgent
from .events import SignalGenerated, RiskCheckPassed, RiskCheckFailed

if TYPE_CHECKING:
    from broker import AlpacaBroker
    from .event_bus import EventBus


class RiskAgent(BaseAgent):
    """Validates signals against risk rules before execution."""

    def __init__(
        self,
        event_bus: "EventBus",
        broker: "AlpacaBroker",
        position_sizer: PositionSizer | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        super().__init__("RiskAgent", event_bus)
        self.broker = broker
        if position_sizer is None:
            import config
            position_sizer = PositionSizer(
                scale_by_strength=config.POSITION_SIZER_SCALE_BY_STRENGTH,
                min_strength=config.POSITION_SIZER_MIN_STRENGTH,
                max_strength=config.POSITION_SIZER_MAX_STRENGTH,
            )
        self.position_sizer = position_sizer
        if circuit_breaker is None:
            import config
            circuit_breaker = CircuitBreaker(
                daily_loss_limit_pct=config.DAILY_LOSS_LIMIT_PCT,
                max_drawdown_pct=config.MAX_DRAWDOWN_PCT,
                market_timezone=config.MARKET_TIMEZONE,
            )
        self.circuit_breaker = circuit_breaker
        self.daily_trades = 0
        self.last_trade_date = None
        self._checks_passed = 0
        self._checks_failed = 0
        self._sector_map_cache = None
        self._sector_map_key = None

    async def start(self):
        """Start listening for signals."""
        await super().start()
        self.event_bus.subscribe(SignalGenerated, self._handle_signal)

    async def stop(self):
        """Stop the agent."""
        self.event_bus.unsubscribe(SignalGenerated, self._handle_signal)
        await super().stop()

    def _reset_daily_limits(self):
        """Reset daily trade count if new day."""
        import config
        try:
            today = datetime.now(ZoneInfo(config.MARKET_TIMEZONE)).date()
        except Exception:
            today = datetime.now().date()
        if self.last_trade_date != today:
            self.daily_trades = 0
            self.last_trade_date = today

    async def _handle_signal(self, signal: SignalGenerated):
        """Validate a signal against risk rules."""
        import config

        self._reset_daily_limits()

        # Skip hold signals
        if signal.action == "hold":
            return

        # Check daily trade limit
        if self.daily_trades >= config.MAX_DAILY_TRADES:
            await self._fail(signal, f"Daily trade limit reached ({config.MAX_DAILY_TRADES})")
            return

        # Get account info
        portfolio_value = self.broker.get_portfolio_value()
        buying_power = self.broker.get_buying_power()
        if portfolio_value <= 0:
            await self._fail(signal, "Invalid portfolio value")
            return

        breaker_active, breaker_reason = self.circuit_breaker.update(portfolio_value)
        if breaker_active and signal.action == "buy":
            await self._fail(signal, f"Circuit breaker active: {breaker_reason}")
            return

        if signal.action == "buy":
            positions = self._get_positions_safe()

            if positions is not None:
                if not self._check_open_positions_limit(positions):
                    await self._fail(signal, f"Max open positions reached ({config.MAX_OPEN_POSITIONS})")
                    return

            # Calculate position size
            trade_value = self.position_sizer.calculate_trade_value(
                signal_strength=signal.strength,
                account_value=portfolio_value,
                buying_power=buying_power,
                max_position_pct=config.MAX_POSITION_PCT,
            )

            # Check minimum trade value
            if trade_value < config.MIN_TRADE_VALUE:
                await self._fail(
                    signal,
                    f"Trade value ${trade_value:.2f} below minimum ${config.MIN_TRADE_VALUE}",
                )
                return

            # Check buying power
            if buying_power < config.MIN_TRADE_VALUE:
                await self._fail(signal, f"Insufficient buying power (${buying_power:.2f})")
                return

            if positions is not None:
                if not self._check_sector_exposure(signal.symbol, trade_value, positions, portfolio_value):
                    await self._fail(signal, "Sector exposure limit reached")
                    return

                if not self._check_correlation_exposure(signal.symbol, trade_value, positions, portfolio_value):
                    await self._fail(signal, "Correlation exposure limit reached")
                    return

            position_pct = trade_value / portfolio_value * 100

            await self._pass(signal, trade_value, position_pct, f"Buy approved: ${trade_value:.2f} ({position_pct:.1f}% of portfolio)")

        elif signal.action == "sell":
            # Check if we have a position
            try:
                position = self.broker.get_position(signal.symbol)
            except Exception as e:
                await self._fail(signal, f"Position lookup failed: {e}")
                return

            if not position:
                await self._fail(signal, f"No position in {signal.symbol} to sell")
                return

            trade_value = float(position.market_value)
            position_pct = trade_value / portfolio_value * 100

            await self._pass(signal, trade_value, position_pct, f"Sell approved: ${trade_value:.2f}")

    async def _pass(self, signal: SignalGenerated, trade_value: float, position_pct: float, reason: str):
        """Emit risk check passed event."""
        self._checks_passed += 1
        event = RiskCheckPassed(
            universe=self.universe,
            session_id=self.session_id,
            source=self.name,
            symbol=signal.symbol,
            action=signal.action,
            trade_value=trade_value,
            position_pct=position_pct,
            reason=reason,
        )
        await self.event_bus.publish(event)

    async def _fail(self, signal: SignalGenerated, reason: str):
        """Emit risk check failed event."""
        self._checks_failed += 1
        event = RiskCheckFailed(
            universe=self.universe,
            session_id=self.session_id,
            source=self.name,
            symbol=signal.symbol,
            action=signal.action,
            reason=reason,
        )
        await self.event_bus.publish(event)

    def increment_trade_count(self):
        """Increment daily trade count after successful execution."""
        self._reset_daily_limits()
        self.daily_trades += 1

    def status(self) -> dict:
        """Get agent status."""
        import config
        base = super().status()
        base["daily_trades"] = self.daily_trades
        base["max_daily_trades"] = config.MAX_DAILY_TRADES
        base["checks_passed"] = self._checks_passed
        base["checks_failed"] = self._checks_failed
        base["circuit_breaker"] = self.circuit_breaker.status()
        base["max_open_positions"] = config.MAX_OPEN_POSITIONS
        return base

    def reset_circuit_breaker(self):
        """Reset the circuit breaker state."""
        self.circuit_breaker.reset()

    def _get_positions_safe(self):
        try:
            return self.broker.get_positions()
        except Exception as e:
            print(f"RiskAgent: Error fetching positions for checks: {e}")
            return None

    def _check_open_positions_limit(self, positions) -> bool:
        import config
        return len(positions) < config.MAX_OPEN_POSITIONS

    def _check_sector_exposure(
        self,
        symbol: str,
        trade_value: float,
        positions,
        portfolio_value: float,
    ) -> bool:
        import config
        if portfolio_value <= 0:
            return True

        sector_map = self._load_sector_map()
        if not sector_map:
            return True

        symbol_upper = symbol.upper()
        sector = sector_map.get(symbol_upper)
        if not sector:
            return True

        sector_value = 0.0
        for position in positions:
            pos_symbol = getattr(position, "symbol", None)
            if not pos_symbol:
                continue
            pos_sector = sector_map.get(str(pos_symbol).upper())
            if pos_sector != sector:
                continue
            sector_value += self._position_market_value(position)

        proposed_value = sector_value + max(trade_value, 0.0)
        exposure_pct = proposed_value / portfolio_value
        return exposure_pct <= config.MAX_SECTOR_EXPOSURE_PCT

    def _check_correlation_exposure(
        self,
        symbol: str,
        trade_value: float,
        positions,
        portfolio_value: float,
    ) -> bool:
        import config
        if portfolio_value <= 0:
            return True
        if not positions:
            return True

        target_returns = self._get_returns(symbol, config.CORRELATION_LOOKBACK_DAYS)
        if target_returns is None or target_returns.empty:
            return True

        correlated_value = 0.0
        target_existing_value = 0.0
        symbol_upper = symbol.upper()

        for position in positions:
            pos_symbol = getattr(position, "symbol", None)
            if not pos_symbol:
                continue
            pos_symbol = str(pos_symbol).upper()
            pos_value = self._position_market_value(position)

            if pos_symbol == symbol_upper:
                target_existing_value += pos_value
                continue

            pos_returns = self._get_returns(pos_symbol, config.CORRELATION_LOOKBACK_DAYS)
            if pos_returns is None or pos_returns.empty:
                continue

            aligned = target_returns.align(pos_returns, join="inner")
            if len(aligned[0]) < 3 or len(aligned[1]) < 3:
                continue

            corr = aligned[0].corr(aligned[1])
            if corr is None:
                continue
            if corr >= config.CORRELATION_THRESHOLD:
                correlated_value += pos_value

        proposed_value = correlated_value + target_existing_value + max(trade_value, 0.0)
        exposure_pct = proposed_value / portfolio_value
        return exposure_pct <= config.MAX_CORRELATED_EXPOSURE_PCT

    def _load_sector_map(self) -> dict:
        import config
        import json
        key = (config.SECTOR_MAP_JSON, config.SECTOR_MAP_PATH)
        if self._sector_map_cache is not None and self._sector_map_key == key:
            return self._sector_map_cache

        raw_map = {}
        if config.SECTOR_MAP_JSON:
            try:
                raw_map = json.loads(config.SECTOR_MAP_JSON)
            except Exception as e:
                print(f"RiskAgent: Error parsing SECTOR_MAP_JSON: {e}")
        elif config.SECTOR_MAP_PATH:
            try:
                with open(config.SECTOR_MAP_PATH, "r", encoding="utf-8") as handle:
                    raw_map = json.load(handle)
            except FileNotFoundError:
                print(f"RiskAgent: Sector map file not found: {config.SECTOR_MAP_PATH}")
            except Exception as e:
                print(f"RiskAgent: Error reading sector map: {e}")

        normalized = {}
        if isinstance(raw_map, dict):
            for key_sym, value in raw_map.items():
                if not key_sym or not value:
                    continue
                normalized[str(key_sym).upper()] = str(value).strip()
        else:
            print("RiskAgent: Sector map must be a JSON object of symbol->sector")

        self._sector_map_cache = normalized
        self._sector_map_key = key
        return normalized

    def _position_market_value(self, position) -> float:
        value = getattr(position, "market_value", 0.0)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _get_returns(self, symbol: str, lookback_days: int):
        import pandas as pd
        try:
            bars = self.broker.get_bars(symbol, days=lookback_days)
        except Exception as e:
            print(f"RiskAgent: Error fetching bars for {symbol}: {e}")
            return None
        if bars is None or len(bars) == 0:
            return None
        try:
            closes = bars["close"]
        except Exception:
            return None
        if closes is None or len(closes) < 3:
            return None
        returns = closes.pct_change().dropna()
        if returns is None or len(returns) < 2:
            return None
        if isinstance(returns, pd.DataFrame):
            returns = returns.iloc[:, 0]
        return returns
