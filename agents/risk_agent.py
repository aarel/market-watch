"""Risk Agent - validates trades before execution."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from risk.circuit_breaker import CircuitBreaker
from risk.exposure_checkers import (
    CorrelationExposureChecker,
    ReturnCalculator,
    RVOLChecker,
    SectorExposureChecker,
    SectorMapLoader,
)
from risk.position_sizer import PositionSizer

from .base import BaseAgent
from .events import RiskCheckFailed, RiskCheckPassed, SignalGenerated

if TYPE_CHECKING:
    from broker import AlpacaBroker

    from .event_bus import EventBus


class RiskAgent(BaseAgent):
    """Validates signals against risk rules before execution.

    Uses BrokerQueryService for cached portfolio/position queries.
    """

    def __init__(
        self,
        event_bus: "EventBus",
        broker: "AlpacaBroker",  # Actually receives BrokerQueryService in production
        position_sizer: PositionSizer | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        sector_map_loader: SectorMapLoader | None = None,
        return_calculator: ReturnCalculator | None = None,
        sector_exposure_checker: SectorExposureChecker | None = None,
        correlation_exposure_checker: CorrelationExposureChecker | None = None,
        rvol_checker: RVOLChecker | None = None,
    ):
        super().__init__("RiskAgent", event_bus)
        self.broker = broker  # BrokerQueryService in production (cached calls)
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

        # Initialize exposure checkers (modular risk validation components)
        self.sector_map_loader = sector_map_loader or SectorMapLoader()
        self.return_calculator = return_calculator or ReturnCalculator(broker)
        self.sector_exposure_checker = sector_exposure_checker or SectorExposureChecker(self.sector_map_loader)
        self.correlation_exposure_checker = correlation_exposure_checker or CorrelationExposureChecker(self.return_calculator)
        self.rvol_checker = rvol_checker or RVOLChecker(broker)

        # Earnings blackout (lazy-init; injected for testing)
        self._earnings_cache = None

        self.daily_trades = 0
        self.last_trade_date = None
        self._checks_passed = 0
        self._checks_failed = 0

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

        # Get account info (async to avoid blocking event loop)
        portfolio_value = await self.broker.get_portfolio_value_async()
        buying_power = await self.broker.get_buying_power_async()
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
                # Check sector exposure using modular checker
                if not self.sector_exposure_checker.check(
                    signal.symbol,
                    trade_value,
                    positions,
                    portfolio_value,
                    config.MAX_SECTOR_EXPOSURE_PCT,
                    config.SECTOR_MAP_JSON,
                    config.SECTOR_MAP_PATH,
                ):
                    await self._fail(signal, "Sector exposure limit reached")
                    return

                # Check correlation exposure using modular checker
                if not self.correlation_exposure_checker.check(
                    signal.symbol,
                    trade_value,
                    positions,
                    portfolio_value,
                    config.MAX_CORRELATED_EXPOSURE_PCT,
                    config.CORRELATION_THRESHOLD,
                    config.CORRELATION_LOOKBACK_DAYS,
                ):
                    await self._fail(signal, "Correlation exposure limit reached")
                    return

            # Check relative volume using modular checker
            if not self.rvol_checker.check(signal.symbol, config.RVOL_THRESHOLD, config.LOOKBACK_DAYS):
                await self._fail(signal, f"Relative volume below threshold ({config.RVOL_THRESHOLD})")
                return

            # Earnings blackout
            if config.EARNINGS_BLACKOUT_DAYS > 0:
                from market_calendar import EarningsCache
                if self._earnings_cache is None:
                    self._earnings_cache = EarningsCache(blackout_days=config.EARNINGS_BLACKOUT_DAYS)
                else:
                    self._earnings_cache.blackout_days = config.EARNINGS_BLACKOUT_DAYS
                if self._earnings_cache.is_in_blackout(signal.symbol):
                    await self._fail(
                        signal,
                        f"Earnings blackout: {signal.symbol} has earnings within "
                        f"{config.EARNINGS_BLACKOUT_DAYS} day(s)",
                    )
                    return

            position_pct = trade_value / portfolio_value * 100

            await self._pass(signal, trade_value, position_pct, f"Buy approved: ${trade_value:.2f} ({position_pct:.1f}% of portfolio)")

        elif signal.action == "sell":
            # Check if we have a position (async to avoid blocking event loop)
            try:
                position = await self.broker.get_position_async(signal.symbol)
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
            signal_reason=signal.reason,
            signal_strength=signal.strength,
            signal_momentum=signal.momentum,
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
            logger.error(f"Error fetching positions for checks: {e}")
            return None

    def _check_open_positions_limit(self, positions) -> bool:
        import config
        return len(positions) < config.MAX_OPEN_POSITIONS
