"""Evaluation routines for observability logs."""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable, Optional

from .expectations import load_expectations
from .models import EvaluationFinding, EvaluationReport


def evaluate_log(
    log_path: str,
    since: Optional[str] = None,
    expectations_path: Optional[str] = None,
) -> EvaluationReport:
    """Evaluate a JSONL log file against expectations."""
    observations = _load_observations(log_path, since)
    metrics, event_counts = _compute_metrics(observations)
    expectations = load_expectations(expectations_path)

    findings: list[EvaluationFinding] = []
    for expectation in expectations:
        agent_metrics = metrics.get(expectation.agent, {})
        value = agent_metrics.get(expectation.metric)
        status = _evaluate_value(value, expectation)
        findings.append(
            EvaluationFinding(
                agent=expectation.agent,
                metric=expectation.metric,
                value=value,
                status=status,
                description=expectation.description,
                min_value=expectation.min_value,
                max_value=expectation.max_value,
                severity=expectation.severity,
            )
        )

    return EvaluationReport(
        generated_at=datetime.now(),
        metrics=metrics,
        findings=findings,
        event_counts=event_counts,
    )


def _load_observations(log_path: str, since: Optional[str]) -> list[dict[str, Any]]:
    if not os.path.exists(log_path):
        return []

    cutoff = None
    if since:
        try:
            cutoff = datetime.fromisoformat(since)
        except ValueError:
            cutoff = None

    observations: list[dict[str, Any]] = []
    with open(log_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if cutoff:
                try:
                    ts = datetime.fromisoformat(record.get("timestamp", ""))
                except ValueError:
                    ts = None
                if ts and ts < cutoff:
                    continue
            observations.append(record)

    return observations


def _compute_metrics(observations: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Optional[float]]], dict[str, int]]:
    metrics: dict[str, dict[str, Optional[float]]] = defaultdict(dict)
    event_counts: dict[str, int] = defaultdict(int)

    market_events = [obs for obs in observations if obs.get("event_type") == "MarketDataReady"]
    signals_updates = [obs for obs in observations if obs.get("event_type") == "SignalsUpdated"]
    risk_passed = [obs for obs in observations if obs.get("event_type") == "RiskCheckPassed"]
    risk_failed = [obs for obs in observations if obs.get("event_type") == "RiskCheckFailed"]
    orders_executed = [obs for obs in observations if obs.get("event_type") == "OrderExecuted"]
    orders_failed = [obs for obs in observations if obs.get("event_type") == "OrderFailed"]
    stop_losses = [obs for obs in observations if obs.get("event_type") == "StopLossTriggered"]

    event_counts["total"] = len(observations)
    event_counts["MarketDataReady"] = len(market_events)
    event_counts["SignalsUpdated"] = len(signals_updates)
    event_counts["RiskCheckPassed"] = len(risk_passed)
    event_counts["RiskCheckFailed"] = len(risk_failed)
    event_counts["OrderExecuted"] = len(orders_executed)
    event_counts["OrderFailed"] = len(orders_failed)
    event_counts["StopLossTriggered"] = len(stop_losses)

    metrics["DataAgent"]["market_data_events"] = float(len(market_events)) if market_events else 0.0
    metrics["DataAgent"]["avg_interval_seconds"] = _average_market_interval(market_events)
    metrics["DataAgent"]["missing_price_ratio"] = _average_ratio(market_events, "missing_price_ratio")
    metrics["DataAgent"]["bars_coverage_ratio"] = _average_ratio(market_events, "bars_coverage_ratio")

    metrics["SignalAgent"]["actionable_ratio"] = _average_ratio(signals_updates, "actionable_ratio")
    metrics["SignalAgent"]["signal_error_ratio"] = _average_ratio(signals_updates, "signal_error_ratio")

    total_risk = len(risk_passed) + len(risk_failed)
    metrics["RiskAgent"]["risk_fail_ratio"] = (len(risk_failed) / total_risk) if total_risk else None

    total_orders = len(orders_executed) + len(orders_failed)
    metrics["ExecutionAgent"]["order_failure_ratio"] = (len(orders_failed) / total_orders) if total_orders else None

    metrics["MonitorAgent"]["stop_loss_count"] = float(len(stop_losses))

    return metrics, dict(event_counts)


def _average_market_interval(market_events: list[dict[str, Any]]) -> Optional[float]:
    if len(market_events) < 2:
        return None
    timestamps = []
    for obs in market_events:
        try:
            timestamps.append(datetime.fromisoformat(obs.get("timestamp", "")))
        except ValueError:
            continue
    if len(timestamps) < 2:
        return None
    timestamps.sort()
    intervals = [
        (timestamps[i] - timestamps[i - 1]).total_seconds()
        for i in range(1, len(timestamps))
    ]
    return sum(intervals) / len(intervals) if intervals else None


def _average_ratio(observations: list[dict[str, Any]], metric_key: str) -> Optional[float]:
    values = []
    for obs in observations:
        outputs = obs.get("outputs", {})
        value = outputs.get(metric_key)
        if isinstance(value, (int, float)):
            values.append(value)
    if not values:
        return None
    return sum(values) / len(values)


def _evaluate_value(value: Optional[float], expectation) -> str:
    if value is None:
        return "missing"

    if expectation.min_value is not None and value < expectation.min_value:
        return "fail" if expectation.severity == "fail" else "warn"
    if expectation.max_value is not None and value > expectation.max_value:
        return "fail" if expectation.severity == "fail" else "warn"
    return "ok"
