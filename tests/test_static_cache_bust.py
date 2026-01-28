import re
import unittest
from pathlib import Path


class TestStaticCacheBust(unittest.TestCase):
    def test_asset_version_defined(self):
        text = Path("static/index.html").read_text(encoding="utf-8")
        self.assertIn("ASSET_VERSION", text)
        # ensure favicon has version param
        self.assertRegex(text, r"/img/favicon\.png\?v=")

    def test_api_fetch_adds_cache_param(self):
        text = Path("static/index.html").read_text(encoding="utf-8")
        self.assertIn("if (url.startsWith('/') && !url.includes('_v='))", text)
        self.assertIn("apiFetch(`/api/analytics/equity?period=", text)


if __name__ == "__main__":
    unittest.main()
