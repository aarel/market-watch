import importlib.util
import sys
from pathlib import Path


def test_conftest_adds_repo_root_to_sys_path():
    conftest_path = Path(__file__).resolve().parents[1] / "conftest.py"
    root_str = str(conftest_path.parent)

    original_sys_path = list(sys.path)
    try:
        # Remove repo root if present so we can assert insertion
        sys.path[:] = [p for p in sys.path if p != root_str]

        spec = importlib.util.spec_from_file_location("conftest_under_test", conftest_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        assert root_str in sys.path
    finally:
        sys.path[:] = original_sys_path
