import unittest
from unittest.mock import patch
import os

# Disable heavy FastAPI lifespan during unit tests
os.environ.setdefault("FASTAPI_DISABLE_LIFESPAN", "1")

from fastapi import HTTPException
from starlette.requests import Request

import server


def _make_request(client_host="127.0.0.1", origin=None, headers=None):
    raw_headers = []
    if origin:
        raw_headers.append((b"origin", origin.encode("utf-8")))
    if headers:
        for key, value in headers.items():
            raw_headers.append((key.lower().encode("utf-8"), value.encode("utf-8")))

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/trade",
        "headers": raw_headers,
        "client": (client_host, 1234),
        "scheme": "http",
    }
    return Request(scope)


class TestApiAccess(unittest.TestCase):
    def test_requires_token_when_configured(self):
        request = _make_request(origin="http://localhost:8000")
        with patch.object(server.config, "API_TOKEN", "secret"), \
            patch.object(server.config, "ALLOWED_ORIGINS", ["http://localhost:8000"]):
            with self.assertRaises(HTTPException) as ctx:
                server.require_api_access(request)
            self.assertEqual(ctx.exception.status_code, 401)

    def test_accepts_valid_token(self):
        request = _make_request(
            origin="http://localhost:8000",
            headers={"X-API-Key": "secret"},
        )
        with patch.object(server.config, "API_TOKEN", "secret"), \
            patch.object(server.config, "ALLOWED_ORIGINS", ["http://localhost:8000"]):
            server.require_api_access(request)

    def test_blocks_non_loopback_without_token(self):
        request = _make_request(client_host="10.0.0.5")
        with patch.object(server.config, "API_TOKEN", ""), \
            patch.object(server.config, "ALLOWED_ORIGINS", ["http://localhost:8000"]):
            with self.assertRaises(HTTPException) as ctx:
                server.require_api_access(request)
            self.assertEqual(ctx.exception.status_code, 403)

    def test_blocks_disallowed_origin(self):
        request = _make_request(origin="http://evil.example")
        with patch.object(server.config, "API_TOKEN", ""), \
            patch.object(server.config, "ALLOWED_ORIGINS", ["http://localhost:8000"]):
            with self.assertRaises(HTTPException) as ctx:
                server.require_api_access(request)
            self.assertEqual(ctx.exception.status_code, 403)

    def test_allows_loopback_with_allowed_origin(self):
        request = _make_request(origin="http://localhost:8000")
        with patch.object(server.config, "API_TOKEN", ""), \
            patch.object(server.config, "ALLOWED_ORIGINS", ["http://localhost:8000"]):
            server.require_api_access(request)


if __name__ == "__main__":
    unittest.main()
