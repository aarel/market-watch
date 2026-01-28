"""Render human-readable evaluation reports."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .models import EvaluationReport


def render_report(report: EvaluationReport) -> str:
    """Render a narrative report from evaluation data."""
    status_counts = defaultdict(int)
    for finding in report.findings:
        status_counts[finding.status] += 1

    lines = []
    lines.append("Observability Evaluation Report")
    lines.append(f"Generated: {report.generated_at.isoformat()}")
    lines.append("")

    lines.append("Summary")
    lines.append(f"- ok: {status_counts['ok']}")
    lines.append(f"- warn: {status_counts['warn']}")
    lines.append(f"- fail: {status_counts['fail']}")
    lines.append(f"- missing: {status_counts['missing']}")
    lines.append("")

    lines.append("Findings")
    for finding in report.findings:
        if finding.status == "ok":
            continue
        bounds = []
        if finding.min_value is not None:
            bounds.append(f">= {finding.min_value}")
        if finding.max_value is not None:
            bounds.append(f"<= {finding.max_value}")
        bounds_text = ", ".join(bounds) if bounds else "n/a"
        lines.append(
            f"- [{finding.status.upper()}] {finding.agent}.{finding.metric}: {finding.value} (expected {bounds_text})"
        )
        lines.append(f"  {finding.description}")

    if all(f.status == "ok" for f in report.findings):
        lines.append("- All monitored expectations are within bounds.")

    lines.append("")
    lines.append("Event Counts")
    for key, value in report.event_counts.items():
        lines.append(f"- {key}: {value}")

    return "\n".join(lines)
