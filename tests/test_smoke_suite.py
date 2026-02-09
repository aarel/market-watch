import os

os.environ.setdefault("FASTAPI_DISABLE_LIFESPAN", "1")

import pytest
from fastapi.testclient import TestClient

from server import app
from server.config_manager import ConfigManager


pytestmark = [pytest.mark.smoke, pytest.mark.blackbox]


def test_health_endpoint_smoke():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "checks" in data


def test_config_manager_smoke(tmp_path):
    config_path = tmp_path / "config_state.json"
    manager = ConfigManager(path=str(config_path))
    manager.save()
    assert config_path.exists()
