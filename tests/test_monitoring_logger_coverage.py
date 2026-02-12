import json
from datetime import datetime
from unittest.mock import patch

import pytest

from monitoring.logger import JSONLLogger, SystemLogWriter, _json_default
from universe import Universe


def test_jsonl_logger_writes_and_creates_dir(tmp_path):
    log_path = tmp_path / "logs" / "app.jsonl"
    logger = JSONLLogger(str(log_path), max_mb=0)

    record = {"ts": datetime(2024, 1, 1), "value": 1}
    logger.write(record)

    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8").strip()
    data = json.loads(content)
    assert data["value"] == 1
    assert "2024" in data["ts"]


def test_jsonl_logger_rotation(tmp_path):
    log_path = tmp_path / "app.jsonl"
    log_path.write_text("XXX")

    class FixedDateTime:
        @classmethod
        def now(cls):
            return datetime(2024, 1, 1, 12, 0, 0)

    logger = JSONLLogger(str(log_path), max_mb=0.000002)  # ~2 bytes

    with patch("monitoring.logger.datetime", FixedDateTime):
        logger.write({"value": 1})

    rotated = tmp_path / "app.jsonl.20240101_120000"
    assert rotated.exists()
    assert log_path.exists()


def test_jsonl_logger_no_rotation_when_under_limit(tmp_path):
    log_path = tmp_path / "app.jsonl"
    log_path.write_text("X")
    logger = JSONLLogger(str(log_path), max_mb=0.1)
    logger._rotate_if_needed()
    assert log_path.exists()


def test_jsonl_logger_no_rotation_when_missing_file(tmp_path):
    log_path = tmp_path / "missing.jsonl"
    logger = JSONLLogger(str(log_path), max_mb=0.1)
    logger._rotate_if_needed()
    assert not log_path.exists()


def test_json_default():
    assert _json_default(datetime(2024, 1, 1, 0, 0, 0)) == "2024-01-01T00:00:00"
    assert _json_default(5) == "5"


def test_system_log_writer_writes_and_sets_universe(tmp_path):
    writer = SystemLogWriter(Universe.SIMULATION, base_dir=tmp_path)
    writer.write({"message": "hello"})

    assert writer.path.exists()
    line = writer.path.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["universe"] == "simulation"
    assert payload["message"] == "hello"


def test_system_log_writer_universe_mismatch(tmp_path):
    writer = SystemLogWriter(Universe.SIMULATION, base_dir=tmp_path)
    with pytest.raises(ValueError):
        writer.write({"universe": "live"})


def test_system_log_writer_rotation(tmp_path):
    writer = SystemLogWriter(Universe.SIMULATION, base_dir=tmp_path, max_mb=0.000002)
    writer.path.parent.mkdir(parents=True, exist_ok=True)
    writer.path.write_text("XXXX")

    class FixedDateTime:
        @classmethod
        def now(cls):
            return datetime(2024, 1, 1, 12, 0, 0)

    with patch("monitoring.logger.datetime", FixedDateTime):
        writer.write({"message": "rotate"})

    rotated = writer.path.with_suffix(writer.path.suffix + ".20240101_120000")
    assert rotated.exists()
    assert writer.path.exists()


def test_system_log_writer_no_rotation_when_under_limit(tmp_path):
    writer = SystemLogWriter(Universe.SIMULATION, base_dir=tmp_path, max_mb=0.1)
    writer.path.parent.mkdir(parents=True, exist_ok=True)
    writer.path.write_text("X")
    writer._rotate_if_needed()
    assert writer.path.exists()


def test_system_log_writer_no_rotation_when_disabled(tmp_path):
    writer = SystemLogWriter(Universe.SIMULATION, base_dir=tmp_path, max_mb=0)
    writer._rotate_if_needed()
    assert writer.max_bytes == 0
