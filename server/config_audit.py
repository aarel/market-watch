"""Config audit trail: fire-and-forget JSONL append on every config save."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def append_audit(
    universe_value: str,
    old_config: dict[str, Any],
    new_config: dict[str, Any],
) -> None:
    """
    Append a config-change record to logs/{universe}/config_changes.jsonl.

    Never raises — silently swallows all I/O errors so this never blocks
    a config save.

    Args:
        universe_value: Universe enum .value string (e.g. "paper")
        old_config: Config snapshot before the update
        new_config: Config snapshot after the update
    """
    try:
        changed = {
            k: {"from": old_config.get(k), "to": v}
            for k, v in new_config.items()
            if v != old_config.get(k)
        }
        if not changed:
            return

        record = {
            "timestamp": datetime.now().isoformat(),
            "universe": universe_value,
            "changed": changed,
        }

        path = Path(f"logs/{universe_value}/config_changes.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    except Exception:
        pass  # Never crash the config pipeline
