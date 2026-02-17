import importlib
import os
import re

from fastapi.testclient import TestClient


def _load_app_with_noop_lifespan():
    os.environ["FASTAPI_DISABLE_LIFESPAN"] = "1"
    os.environ["MARKET_WATCH_DEMO_MODE"] = "0"
    module = importlib.import_module("server.main")
    module = importlib.reload(module)
    app = module.app
    # Ensure each test uses an isolated registry instance.
    app.state.metrics = module.create_metrics()
    return app, module


def test_create_metrics_returns_isolated_registries():
    app, module = _load_app_with_noop_lifespan()
    m1 = module.create_metrics()
    m2 = module.create_metrics()
    assert m1["registry"] is not m2["registry"]
    assert m1["request_count"] is not m2["request_count"]
    assert m1["request_error_count"] is not m2["request_error_count"]
    assert m1["request_latency"] is not m2["request_latency"]


def test_metrics_endpoint_exists_and_has_expected_series():
    app, _module = _load_app_with_noop_lifespan()
    with TestClient(app) as client:
        client.get("/api/health")
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    body = response.text
    assert "http_requests_total" in body
    assert "http_request_errors_total" in body
    assert "http_request_duration_seconds" in body


def test_error_and_latency_metrics_increment_after_failing_route():
    app, _module = _load_app_with_noop_lifespan()
    with TestClient(app) as client:
        client.get("/api/config")
        metrics = client.get("/metrics")

    text = metrics.text
    assert re.search(r"http_request_duration_seconds_count\{[^}]*\}\s+[0-9.]+", text)
    assert re.search(r"http_request_errors_total\{[^}]*\}\s+[0-9.]+", text)
