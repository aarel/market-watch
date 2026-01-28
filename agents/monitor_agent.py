"""Monitor Agent - watches positions for stop-loss and alerts."""
import asyncio
from typing import TYPE_CHECKING

from .base import BaseAgent
from .events import StopLossTriggered

if TYPE_CHECKING:
    from broker import AlpacaBroker
    from .event_bus import EventBus


class MonitorAgent(BaseAgent):
    """Monitors positions for stop-loss triggers."""

    def __init__(self, event_bus: "EventBus", broker: "AlpacaBroker", check_interval_seconds: int = 120):
        super().__init__("MonitorAgent", event_bus)
        self.broker = broker
        self.check_interval = check_interval_seconds
        self._stop_losses_triggered = 0
        self._last_check = None

    async def start(self):
        """Start the monitoring loop."""
        await super().start()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop the monitoring loop."""
        await super().stop()

    async def _run_loop(self):
        """Main loop that checks positions periodically."""
        while self.running:
            try:
                # Only check if market is open
                if self.broker.is_market_open():
                    await self.check_positions()
            except Exception as e:
                print(f"MonitorAgent error: {e}")

            await asyncio.sleep(self.check_interval)

    async def check_positions(self):
        """Check all positions for stop-loss conditions."""
        import config
        from datetime import datetime

        self._last_check = datetime.now()
        positions = self.broker.get_positions()

        for position in positions:
            symbol = position.symbol
            entry_price = float(position.avg_entry_price)
            current_price = self.broker.get_current_price(symbol)

            if current_price is None:
                continue

            # Calculate loss percentage
            loss_pct = (current_price - entry_price) / entry_price

            # Check stop loss
            if loss_pct <= -config.STOP_LOSS_PCT:
                self._stop_losses_triggered += 1

                event = StopLossTriggered(
                    universe=self.universe,
                    session_id=self.session_id,
                    source=self.name,
                    symbol=symbol,
                    entry_price=entry_price,
                    current_price=current_price,
                    loss_pct=abs(loss_pct),
                    position_value=float(position.market_value),
                )
                await self.event_bus.publish(event)

    def status(self) -> dict:
        """Get agent status."""
        base = super().status()
        base["check_interval_seconds"] = self.check_interval
        base["last_check"] = self._last_check.isoformat() if self._last_check else None
        base["stop_losses_triggered"] = self._stop_losses_triggered
        return base
