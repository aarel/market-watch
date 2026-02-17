import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "governance" / "calc_release_quality.py"
THRESH_SCRIPT = ROOT / "scripts" / "governance" / "check_release_quality_thresholds.py"
SAMPLE = ROOT / "reports" / "governance" / "deployments.sample.json"


def test_kpi_script_produces_valid_output(tmp_path):
    out = tmp_path / "release_quality.json"
    result = subprocess.run(
        ["python3", str(SCRIPT), "--input", str(SAMPLE), "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "lead_time_hours" in payload
    assert "change_failure_rate" in payload
    assert payload["totals"]["deployments"] >= 1


def test_kpi_script_fails_when_input_missing(tmp_path):
    out = tmp_path / "x.json"
    missing = tmp_path / "missing.json"
    result = subprocess.run(
        ["python3", str(SCRIPT), "--input", str(missing), "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Input file not found" in (result.stderr + result.stdout)


def test_threshold_script_blocks_on_violations(tmp_path):
    report = tmp_path / "release_quality.json"
    report.write_text(
        json.dumps(
            {
                "lead_time_hours": {"p50": 30, "p90": 90},
                "change_failure_rate": {"percent": 50.0},
                "targets": {
                    "lead_time_p50_hours_max": 24,
                    "lead_time_p90_hours_max": 72,
                    "change_failure_rate_percent_max": 15,
                },
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["python3", str(THRESH_SCRIPT), "--input", str(report)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "FAIL:" in (result.stdout + result.stderr)


def test_threshold_script_passes_when_within_targets(tmp_path):
    report = tmp_path / "release_quality.json"
    report.write_text(
        json.dumps(
            {
                "lead_time_hours": {"p50": 4, "p90": 8},
                "change_failure_rate": {"percent": 2.0},
                "targets": {
                    "lead_time_p50_hours_max": 24,
                    "lead_time_p90_hours_max": 72,
                    "change_failure_rate_percent_max": 15,
                },
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["python3", str(THRESH_SCRIPT), "--input", str(report)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "PASS:" in result.stdout


def test_ci_workflow_contains_threshold_gate_step():
    workflow = (ROOT / ".github" / "workflows" / "release-quality-metrics.yml").read_text(encoding="utf-8")
    assert "check_release_quality_thresholds.py" in workflow
