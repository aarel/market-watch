"""Data models for observability logging and evaluation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Observation:
    """Structured log entry emitted from event bus activity."""
    timestamp: datetime
    event_type: str
    agent: str
    action: Optional[str] = None
    symbol: Optional[str] = None
    outcome: Optional[str] = None
    reason: Optional[str] = None
    reason_code: Optional[str] = None
    latency_ms: Optional[float] = None
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "agent": self.agent,
            "action": self.action,
            "symbol": self.symbol,
            "outcome": self.outcome,
            "reason": self.reason,
            "reason_code": self.reason_code,
            "latency_ms": self.latency_ms,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "context": self.context,
        }


@dataclass
class Expectation:
    """Metric expectation definition."""
    agent: str
    metric: str
    description: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    severity: str = "warn"  # warn or fail


@dataclass
class EvaluationFinding:
    """Result of evaluating a metric against an expectation."""
    agent: str
    metric: str
    value: Optional[float]
    status: str
    description: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    severity: str = "warn"


@dataclass
class EvaluationReport:
    """Aggregated evaluation results."""
    generated_at: datetime
    metrics: dict[str, dict[str, Optional[float]]]
    findings: list[EvaluationFinding]
    event_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "metrics": self.metrics,
            "findings": [
                {
                    "agent": f.agent,
                    "metric": f.metric,
                    "value": f.value,
                    "status": f.status,
                    "description": f.description,
                    "min_value": f.min_value,
                    "max_value": f.max_value,
                    "severity": f.severity,
                }
                for f in self.findings
            ],
            "event_counts": self.event_counts,
        }
