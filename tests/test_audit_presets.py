import json
import unittest
from pathlib import Path


class TestAuditPresets(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]
        self.presets_path = self.repo_root / "audit_presets.json"

    def test_preset_file_structure(self):
        self.assertTrue(self.presets_path.exists())
        data = json.loads(self.presets_path.read_text(encoding="utf-8"))
        self.assertIn("dra", data)
        self.assertIn("clean_code", data)
        self.assertIn("tests", data)
        self.assertTrue(isinstance(data["dra"], dict))
        self.assertTrue(isinstance(data["clean_code"], dict))
        self.assertTrue(isinstance(data["tests"], dict))
        self.assertGreater(len(data["dra"]), 0)
        self.assertGreater(len(data["clean_code"]), 0)
        self.assertGreater(len(data["tests"]), 0)
        for section in ("dra", "clean_code"):
            for name, preset in data[section].items():
                self.assertIn("target", preset, msg=f"{section}.{name} missing target")
                self.assertIn("scope", preset, msg=f"{section}.{name} missing scope")
                self.assertIsInstance(preset["target"], str)
                self.assertIsInstance(preset["scope"], str)
                self.assertTrue(preset["target"].strip())
                self.assertTrue(preset["scope"].strip())
        for name, preset in data["tests"].items():
            self.assertIn("marker", preset, msg=f"tests.{name} missing marker")
            self.assertIsInstance(preset["marker"], str)

    def test_loader_reads_presets(self):
        from scripts import dev_tools_tui
        presets = dev_tools_tui.load_audit_presets(self.presets_path)
        self.assertIn("dra", presets)
        self.assertIn("clean_code", presets)
        self.assertIn("tests", presets)
        self.assertIn("Agents", presets["dra"])
        self.assertIn("Architecture", presets["clean_code"])
        self.assertIn("All", presets["tests"])


if __name__ == "__main__":
    unittest.main()
