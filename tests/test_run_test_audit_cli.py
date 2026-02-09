import io
import contextlib

from scripts import run_test_audit


def test_run_test_audit_handles_dataclass_summary(monkeypatch, tmp_path):
    class DummyCoverage:
        def __init__(self):
            self.covered_percent = 99.0
            self.missing_files = []

    class DummyTestValidity:
        def __init__(self):
            self.tests_without_asserts = []
            self.skipped_tests = []

    class DummyAgent:
        def run_audit(self, run_tests=True, run_coverage=True, verbose=False):
            return {
                "run_dir": str(tmp_path / "run"),
                "coverage": DummyCoverage(),
                "test_validity": DummyTestValidity(),
            }

    monkeypatch.setattr(run_test_audit, "TestAuditAgent", lambda repo_root=None: DummyAgent())
    monkeypatch.setattr(run_test_audit.sys, "argv", ["run_test_audit"])

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        run_test_audit.main()

    output = stdout.getvalue()
    assert "Test audit complete" in output
    assert "Coverage" in output
