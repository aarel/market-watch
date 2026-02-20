import re
import unittest
from pathlib import Path


class TestStaticCacheBust(unittest.TestCase):
    def test_asset_version_defined(self):
        text = Path("static/index.html").read_text(encoding="utf-8")
        # Verify ASSET_VERSION constant exists for cache-busting
        self.assertIn("const ASSET_VERSION", text)
        # Verify it's assigned a version value
        self.assertRegex(text, r"const ASSET_VERSION\s*=\s*['\"]v[\d.]+['\"]")

    def test_api_fetch_adds_cache_param(self):
        text = Path("static/index.html").read_text(encoding="utf-8")
        self.assertIn("if (url.startsWith('/') && !url.includes('_v='))", text)
        self.assertIn("apiFetch(`/api/analytics/equity?period=", text)


if __name__ == "__main__":
    unittest.main()
