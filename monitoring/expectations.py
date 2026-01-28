"""Default expectations and loading for observability evaluation."""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Iterable

import config

from .models import Expectation


DEFAULT_EXPECTATIONS = [
    # DataAgent
    Expectation(
        agent="DataAgent",
        metric="market_data_events",
        description="At least one market data refresh per evaluation window",
        min_value=1,
        severity="fail",
    ),
    Expectation(
        agent="DataAgent",
        metric="avg_interval_seconds",
        description="Market data refresh interval within 1.5x configured cadence",
        max_value=max(config.TRADE_INTERVAL_MINUTES * 60 * 1.5, 1),
        severity="warn",
    ),
    Expectation(
        agent="DataAgent",
        metric="missing_price_ratio",
        description="Price coverage should be high",
        max_value=0.2,
        severity="warn",
    ),
    Expectation(
        agent="DataAgent",
        metric="bars_coverage_ratio",
        description="Bars coverage should be high",
        min_value=0.8,
        severity="warn",
    ),
    # SignalAgent
    Expectation(
        agent="SignalAgent",
        metric="actionable_ratio",
        description="Actionable signals should be a minority of total signals",
        max_value=0.6,
        severity="warn",
    ),
    Expectation(
        agent="SignalAgent",
        metric="signal_error_ratio",
        description="Signal generation errors should be rare",
        max_value=0.05,
        severity="warn",
    ),
    # RiskAgent
    Expectation(
        agent="RiskAgent",
        metric="risk_fail_ratio",
        description="Risk rejections should be within expected bounds",
        max_value=0.7,
        severity="warn",
    ),
    # ExecutionAgent
    Expectation(
        agent="ExecutionAgent",
        metric="order_failure_ratio",
        description="Order failures should be rare",
        max_value=0.1,
        severity="warn",
    ),
    # MonitorAgent
    Expectation(
        agent="MonitorAgent",
        metric="stop_loss_count",
        description="Stop-loss triggers should stay within normal bounds",
        max_value=5,
        severity="warn",
    ),
]


def load_expectations(path: str | None = None) -> list[Expectation]:
    """Load expectations from JSON, falling back to defaults."""
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return [Expectation(**item) for item in raw]

    return DEFAULT_EXPECTATIONS


def dump_defaults(path: str):
    """Write default expectations to disk for customization."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump([asdict(item) for item in DEFAULT_EXPECTATIONS], handle, indent=2)
