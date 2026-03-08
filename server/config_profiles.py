"""Config profile storage: save/list/load/delete named configs."""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

_PROFILES_DIR = Path("data/profiles")
_NAME_RE = re.compile(r'^[A-Za-z0-9_\-]{1,64}$')


def _validate_name(name: str) -> None:
    """Raise ValueError if the profile name is invalid."""
    if not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid profile name '{name}'. "
            "Use 1-64 characters: letters, digits, underscore, hyphen."
        )


def _profile_path(name: str) -> Path:
    return _PROFILES_DIR / f"{name}.json"


def list_profiles() -> list[dict[str, Any]]:
    """Return metadata for all saved profiles, newest first."""
    if not _PROFILES_DIR.exists():
        return []
    results = []
    for f in sorted(_PROFILES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            saved_at = data.get("_saved_at", "")
        except Exception:
            saved_at = ""
        results.append({"name": f.stem, "saved_at": saved_at})
    return results


def save_profile(name: str, config_dict: dict[str, Any]) -> None:
    """Persist current config as a named profile."""
    _validate_name(name)
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    payload = dict(config_dict)
    payload["_saved_at"] = datetime.now().isoformat()
    _profile_path(name).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_profile(name: str) -> dict[str, Any]:
    """Load a profile's config dict. Strips internal metadata keys."""
    _validate_name(name)
    path = _profile_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Profile '{name}' does not exist.")
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def delete_profile(name: str) -> bool:
    """Delete a profile. Returns True if deleted, False if it didn't exist."""
    _validate_name(name)
    path = _profile_path(name)
    if not path.exists():
        return False
    path.unlink()
    return True
