"""Deterministic request lifecycle transitions for SQLite communicate engine."""

from __future__ import annotations

ALLOWED_TRANSITIONS = {
    "NEW": {"ACKED", "IN_PROGRESS", "BLOCKED"},
    "ACKED": {"IN_PROGRESS", "BLOCKED"},
    "IN_PROGRESS": {"DONE", "BLOCKED"},
    "BLOCKED": {"IN_PROGRESS"},
    "DONE": set(),
    "INPUT_PAD": {"IN_PROGRESS"},  # legacy compatibility
}


def assert_transition(previous_status: str, new_status: str) -> None:
    prev = (previous_status or "").upper()
    new = (new_status or "").upper()
    allowed = ALLOWED_TRANSITIONS.get(prev)
    if allowed is None:
        raise ValueError(f"Unknown previous status: {previous_status}")
    if new not in allowed:
        raise ValueError(f"Invalid status transition: {previous_status} -> {new_status}")
