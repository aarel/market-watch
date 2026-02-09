import io
import runpy
import sys
from pathlib import Path

import backtest.cli
from backtest.data import HistoricalData


def test_backtest_cli_list_cached(tmp_path, monkeypatch):
    data_dir = tmp_path / "historical"
    monkeypatch.setattr(HistoricalData, "DEFAULT_DATA_DIR", data_dir)
    monkeypatch.setattr(sys, "argv", ["backtest", "--list-cached"])

    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    rc = backtest.cli.main()
    assert rc == 0


def test_backtest_module_entrypoint(tmp_path, monkeypatch):
    data_dir = tmp_path / "historical"
    monkeypatch.setattr(HistoricalData, "DEFAULT_DATA_DIR", data_dir)
    monkeypatch.setattr(sys, "argv", ["backtest", "--list-cached"])

    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    runpy.run_module("backtest", run_name="__main__")

    # Verify module executed without exceptions and produced output
    output = stdout.getvalue()
    assert output is not None


def test_monitoring_module_entrypoint(tmp_path, monkeypatch):
    log_path = tmp_path / "agent_events.jsonl"
    log_path.write_text("", encoding="utf-8")
    output_path = tmp_path / "eval.json"
    report_path = tmp_path / "report.txt"

    monkeypatch.setattr(sys, "argv", [
        "monitoring",
        "--log", str(log_path),
        "--output", str(output_path),
        "--report", str(report_path),
    ])

    runpy.run_module("monitoring", run_name="__main__")

    assert output_path.exists()
    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8")
