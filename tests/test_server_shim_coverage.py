import importlib.util
from pathlib import Path

import server as server_pkg


def test_server_shim_exports_app():
    shim_path = Path(__file__).resolve().parents[1] / "server.py"
    spec = importlib.util.spec_from_file_location("server_shim", shim_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.app is server_pkg.app
    assert module.__all__ == ["app"]
