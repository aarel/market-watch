"""Phase 8 tests: Config Profiles, Export/Import, and Audit Trail."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_config() -> dict:
    return {
        "strategy": "momentum",
        "watchlist": ["SPY", "QQQ"],
        "watchlist_mode": "top_gainers",
        "momentum_threshold": 0.02,
        "sell_threshold": -0.01,
        "stop_loss_pct": 0.05,
        "max_position_pct": 0.5,
        "max_daily_trades": 5,
        "max_open_positions": 20,
        "daily_loss_limit_pct": 0.03,
        "max_drawdown_pct": 0.15,
        "max_sector_exposure_pct": 1.0,
        "max_correlated_exposure_pct": 1.0,
        "rvol_threshold": 0.0,
        "trade_interval": 5,
        "auto_trade": True,
        "top_gainers_count": 20,
        "top_gainers_universe": "large_cap",
        "top_gainers_min_price": 5.0,
        "top_gainers_min_volume": 1000000,
        "alerts_enabled": False,
        "alert_email_enabled": False,
        "alert_webhook_enabled": False,
    }


# ---------------------------------------------------------------------------
# config_profiles module
# ---------------------------------------------------------------------------

class TestConfigProfilesValidation(unittest.TestCase):
    """_validate_name rejects bad profile names."""

    def setUp(self):
        from server.config_profiles import _validate_name
        self._validate = _validate_name

    def test_valid_names_pass(self):
        for name in ["aggressive", "my-profile", "test_1", "A", "a" * 64]:
            with self.subTest(name=name):
                self._validate(name)  # should not raise

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            self._validate("")

    def test_name_too_long_raises(self):
        with self.assertRaises(ValueError):
            self._validate("a" * 65)

    def test_spaces_raise(self):
        with self.assertRaises(ValueError):
            self._validate("my profile")

    def test_slash_raises(self):
        with self.assertRaises(ValueError):
            self._validate("a/b")

    def test_dot_raises(self):
        with self.assertRaises(ValueError):
            self._validate("a.b")


class TestConfigProfilesSaveLoad(unittest.TestCase):
    """save_profile / load_profile / list_profiles / delete_profile."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._patch = patch(
            "server.config_profiles._PROFILES_DIR",
            Path(self._tmpdir.name)
        )
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmpdir.cleanup()

    def test_save_creates_file(self):
        from server.config_profiles import save_profile
        save_profile("test", _base_config())
        path = Path(self._tmpdir.name) / "test.json"
        self.assertTrue(path.exists())

    def test_save_stores_config_values(self):
        from server.config_profiles import save_profile
        cfg = _base_config()
        cfg["strategy"] = "breakout"
        save_profile("myprofile", cfg)
        path = Path(self._tmpdir.name) / "myprofile.json"
        data = json.loads(path.read_text())
        self.assertEqual(data["strategy"], "breakout")

    def test_save_adds_saved_at(self):
        from server.config_profiles import save_profile
        save_profile("ts", _base_config())
        path = Path(self._tmpdir.name) / "ts.json"
        data = json.loads(path.read_text())
        self.assertIn("_saved_at", data)

    def test_load_returns_config(self):
        from server.config_profiles import load_profile, save_profile
        cfg = _base_config()
        cfg["max_daily_trades"] = 99
        save_profile("myprofile", cfg)
        loaded = load_profile("myprofile")
        self.assertEqual(loaded["max_daily_trades"], 99)

    def test_load_strips_metadata_keys(self):
        from server.config_profiles import load_profile, save_profile
        save_profile("clean", _base_config())
        loaded = load_profile("clean")
        for key in loaded:
            self.assertFalse(key.startswith("_"), f"Metadata key not stripped: {key}")

    def test_load_missing_profile_raises(self):
        from server.config_profiles import load_profile
        with self.assertRaises(FileNotFoundError):
            load_profile("doesnotexist")

    def test_list_profiles_empty(self):
        from server.config_profiles import list_profiles
        result = list_profiles()
        self.assertEqual(result, [])

    def test_list_profiles_returns_names(self):
        from server.config_profiles import list_profiles, save_profile
        save_profile("alpha", _base_config())
        save_profile("beta", _base_config())
        names = [p["name"] for p in list_profiles()]
        self.assertIn("alpha", names)
        self.assertIn("beta", names)

    def test_list_profiles_includes_saved_at(self):
        from server.config_profiles import list_profiles, save_profile
        save_profile("ts", _base_config())
        profiles = list_profiles()
        self.assertIn("saved_at", profiles[0])

    def test_delete_existing_profile(self):
        from server.config_profiles import delete_profile, list_profiles, save_profile
        save_profile("todelete", _base_config())
        result = delete_profile("todelete")
        self.assertTrue(result)
        names = [p["name"] for p in list_profiles()]
        self.assertNotIn("todelete", names)

    def test_delete_nonexistent_returns_false(self):
        from server.config_profiles import delete_profile
        result = delete_profile("ghost")
        self.assertFalse(result)

    def test_save_overwrites_existing_profile(self):
        from server.config_profiles import load_profile, save_profile
        cfg1 = _base_config()
        cfg1["strategy"] = "momentum"
        save_profile("overwrite", cfg1)
        cfg2 = _base_config()
        cfg2["strategy"] = "rsi"
        save_profile("overwrite", cfg2)
        loaded = load_profile("overwrite")
        self.assertEqual(loaded["strategy"], "rsi")

    def test_save_invalid_name_raises(self):
        from server.config_profiles import save_profile
        with self.assertRaises(ValueError):
            save_profile("bad name!", _base_config())

    def test_load_invalid_name_raises(self):
        from server.config_profiles import load_profile
        with self.assertRaises(ValueError):
            load_profile("bad name!")

    def test_delete_invalid_name_raises(self):
        from server.config_profiles import delete_profile
        with self.assertRaises(ValueError):
            delete_profile("bad name!")


# ---------------------------------------------------------------------------
# config_audit module
# ---------------------------------------------------------------------------

class TestConfigAudit(unittest.TestCase):
    """append_audit writes JSONL diffs."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmpdir.cleanup()

    def _audit_path(self, universe="paper") -> Path:
        return Path(self._tmpdir.name) / universe / "config_changes.jsonl"

    def _run_audit(self, old, new, universe="paper"):
        from server.config_audit import append_audit
        log_root = Path(self._tmpdir.name)
        with patch("server.config_audit.Path") as MockPath:
            # Make Path(f"logs/{u}/config_changes.jsonl") point to our tmpdir
            real_path = self._audit_path(universe)
            real_path.parent.mkdir(parents=True, exist_ok=True)
            MockPath.return_value = real_path
            append_audit(universe, old, new)
        return real_path

    def test_audit_creates_file(self):
        old = _base_config()
        new = dict(old); new["strategy"] = "rsi"
        path = self._run_audit(old, new)
        self.assertTrue(path.exists())

    def test_audit_records_changed_keys(self):
        old = _base_config()
        new = dict(old); new["strategy"] = "breakout"
        path = self._run_audit(old, new)
        record = json.loads(path.read_text().strip())
        self.assertIn("strategy", record["changed"])

    def test_audit_records_from_to_values(self):
        old = _base_config()
        new = dict(old); new["max_daily_trades"] = 10
        path = self._run_audit(old, new)
        record = json.loads(path.read_text().strip())
        changed = record["changed"]["max_daily_trades"]
        self.assertEqual(changed["from"], 5)
        self.assertEqual(changed["to"], 10)

    def test_audit_no_changes_writes_nothing(self):
        cfg = _base_config()
        path = self._run_audit(cfg, cfg)
        self.assertFalse(path.exists())

    def test_audit_appends_multiple(self):
        old = _base_config()
        new1 = dict(old); new1["strategy"] = "rsi"
        new2 = dict(new1); new2["max_daily_trades"] = 10

        path = self._audit_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        from server.config_audit import append_audit
        with patch("server.config_audit.Path") as MockPath:
            MockPath.return_value = path
            append_audit("paper", old, new1)
            append_audit("paper", new1, new2)

        lines = path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 2)

    def test_audit_includes_timestamp(self):
        old = _base_config()
        new = dict(old); new["strategy"] = "rsi"
        path = self._run_audit(old, new)
        record = json.loads(path.read_text().strip())
        self.assertIn("timestamp", record)

    def test_audit_includes_universe(self):
        old = _base_config()
        new = dict(old); new["strategy"] = "rsi"
        path = self._run_audit(old, new, universe="simulation")
        record = json.loads(path.read_text().strip())
        self.assertEqual(record["universe"], "simulation")

    def test_audit_never_raises_on_io_error(self):
        from server.config_audit import append_audit
        old = _base_config()
        new = dict(old); new["strategy"] = "rsi"
        with patch("server.config_audit.Path") as MockPath:
            MockPath.return_value.parent.mkdir.side_effect = PermissionError("denied")
            # Must not raise
            append_audit("paper", old, new)


# ---------------------------------------------------------------------------
# Router endpoints (unit-level, no server start)
# ---------------------------------------------------------------------------

class TestConfigProfilesRouter(unittest.IsolatedAsyncioTestCase):
    """Test profile router endpoint logic via direct function calls."""

    def _make_cfg(self, snap=None):
        cfg = MagicMock()
        cfg.snapshot.return_value = snap or _base_config()
        cfg.universe = MagicMock()
        cfg.universe.value = "paper"
        return cfg

    async def test_get_profiles_returns_list(self):
        from server.routers.config import get_profiles
        with patch("server.routers.config.list_profiles", return_value=[{"name": "foo", "saved_at": "2026-03-08"}]):
            result = await get_profiles(cfg=self._make_cfg())
        self.assertIn("profiles", result)
        self.assertEqual(result["profiles"][0]["name"], "foo")

    async def test_create_profile_ok(self):
        from server.routers.config import SaveProfileRequest, create_profile
        with patch("server.routers.config.save_profile") as mock_save:
            req = SaveProfileRequest(name="myprofile")
            result = await create_profile(req=req, cfg=self._make_cfg())
        mock_save.assert_called_once()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["name"], "myprofile")

    async def test_create_profile_invalid_name_raises_422(self):
        from fastapi import HTTPException
        from server.routers.config import SaveProfileRequest, create_profile
        req = SaveProfileRequest(name="bad name!")
        with self.assertRaises(HTTPException) as ctx:
            await create_profile(req=req, cfg=self._make_cfg())
        self.assertEqual(ctx.exception.status_code, 422)

    async def test_load_profile_ok(self):
        from server.routers.config import load_profile_endpoint
        snap = _base_config()
        cfg = self._make_cfg(snap)
        with patch("server.routers.config.load_profile", return_value={"strategy": "rsi"}), \
             patch("server.routers.config.configure_alerts"), \
             patch("server.routers.config.append_audit"):
            result = await load_profile_endpoint(name="foo", cfg=cfg)
        self.assertEqual(result["status"], "ok")

    async def test_load_profile_not_found_raises_404(self):
        from fastapi import HTTPException
        from server.routers.config import load_profile_endpoint
        with patch("server.routers.config.load_profile", side_effect=FileNotFoundError("no")):
            with self.assertRaises(HTTPException) as ctx:
                await load_profile_endpoint(name="missing", cfg=self._make_cfg())
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_delete_profile_ok(self):
        from server.routers.config import delete_profile_endpoint
        with patch("server.routers.config.delete_profile", return_value=True):
            result = await delete_profile_endpoint(name="foo", cfg=self._make_cfg())
        self.assertEqual(result["status"], "ok")

    async def test_delete_profile_not_found_raises_404(self):
        from fastapi import HTTPException
        from server.routers.config import delete_profile_endpoint
        with patch("server.routers.config.delete_profile", return_value=False):
            with self.assertRaises(HTTPException) as ctx:
                await delete_profile_endpoint(name="ghost", cfg=self._make_cfg())
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_delete_profile_invalid_name_raises_422(self):
        from fastapi import HTTPException
        from server.routers.config import delete_profile_endpoint
        with self.assertRaises(HTTPException) as ctx:
            await delete_profile_endpoint(name="bad/name", cfg=self._make_cfg())
        self.assertEqual(ctx.exception.status_code, 422)


class TestExportConfig(unittest.IsolatedAsyncioTestCase):

    def _make_cfg(self):
        cfg = MagicMock()
        cfg.snapshot.return_value = _base_config()
        cfg.universe = MagicMock()
        cfg.universe.value = "paper"
        return cfg

    async def test_export_returns_response(self):
        from fastapi import Response
        from server.routers.config import export_config
        result = await export_config(cfg=self._make_cfg())
        self.assertIsInstance(result, Response)

    async def test_export_content_is_valid_json(self):
        from server.routers.config import export_config
        result = await export_config(cfg=self._make_cfg())
        data = json.loads(result.body)
        self.assertIn("strategy", data)

    async def test_export_has_content_disposition(self):
        from server.routers.config import export_config
        result = await export_config(cfg=self._make_cfg())
        cd = result.headers.get("content-disposition", "")
        self.assertIn("attachment", cd)
        self.assertIn(".json", cd)

    async def test_export_adds_exported_at(self):
        from server.routers.config import export_config
        result = await export_config(cfg=self._make_cfg())
        data = json.loads(result.body)
        self.assertIn("_exported_at", data)


class TestImportConfig(unittest.IsolatedAsyncioTestCase):

    def _make_cfg(self):
        cfg = MagicMock()
        cfg.snapshot.return_value = _base_config()
        cfg.universe = MagicMock()
        cfg.universe.value = "paper"
        return cfg

    def _make_upload(self, content: dict | str, filename="config.json"):
        data = json.dumps(content) if isinstance(content, dict) else content
        upload = MagicMock()
        upload.filename = filename
        upload.read = MagicMock(return_value=data.encode())
        # Make it awaitable
        import asyncio
        upload.read = MagicMock(side_effect=lambda: asyncio.coroutine(lambda: data.encode())())

        async def async_read():
            return data.encode()
        upload.read = async_read
        return upload

    async def test_import_valid_json_succeeds(self):
        from server.routers.config import import_config
        cfg = self._make_cfg()
        upload = self._make_upload({"strategy": "rsi"})
        with patch("server.routers.config.configure_alerts"), \
             patch("server.routers.config.append_audit"):
            result = await import_config(file=upload, cfg=cfg)
        self.assertEqual(result["status"], "ok")

    async def test_import_wrong_extension_raises_422(self):
        from fastapi import HTTPException
        from server.routers.config import import_config
        upload = self._make_upload("{}", filename="config.txt")
        with self.assertRaises(HTTPException) as ctx:
            await import_config(file=upload, cfg=self._make_cfg())
        self.assertEqual(ctx.exception.status_code, 422)

    async def test_import_invalid_json_raises_422(self):
        from fastapi import HTTPException
        from server.routers.config import import_config
        upload = self._make_upload("NOT_JSON_AT_ALL", filename="config.json")
        with self.assertRaises(HTTPException) as ctx:
            await import_config(file=upload, cfg=self._make_cfg())
        self.assertEqual(ctx.exception.status_code, 422)

    async def test_import_strips_metadata_keys(self):
        from server.routers.config import import_config
        cfg = self._make_cfg()
        upload = self._make_upload({"strategy": "rsi", "_exported_at": "2026-01-01"})
        with patch("server.routers.config.configure_alerts"), \
             patch("server.routers.config.append_audit"):
            await import_config(file=upload, cfg=cfg)
        call_args = cfg.apply_updates.call_args[0][0]
        self.assertNotIn("_exported_at", call_args)

    async def test_import_calls_save_and_configure(self):
        from server.routers.config import import_config
        cfg = self._make_cfg()
        upload = self._make_upload({"strategy": "rsi"})
        with patch("server.routers.config.configure_alerts") as mock_ca, \
             patch("server.routers.config.append_audit"):
            await import_config(file=upload, cfg=cfg)
        cfg.save.assert_called_once()
        mock_ca.assert_called_once()


# ---------------------------------------------------------------------------
# update_config now writes audit trail
# ---------------------------------------------------------------------------

class TestUpdateConfigAudit(unittest.IsolatedAsyncioTestCase):

    async def test_update_config_calls_append_audit(self):
        from server.routers.config import ConfigUpdate, update_config
        cfg = MagicMock()
        cfg.snapshot.return_value = _base_config()
        cfg.universe = MagicMock()
        cfg.universe.value = "paper"

        updates = ConfigUpdate(strategy="rsi")
        with patch("server.routers.config.configure_alerts"), \
             patch("server.routers.config.append_audit") as mock_audit:
            await update_config(updates=updates, cfg=cfg)
        mock_audit.assert_called_once()

    async def test_update_config_passes_old_and_new_to_audit(self):
        from server.routers.config import ConfigUpdate, update_config
        old_snap = _base_config()
        new_snap = dict(old_snap); new_snap["strategy"] = "rsi"

        cfg = MagicMock()
        cfg.snapshot.side_effect = [old_snap, new_snap]  # first call = old, second = new
        cfg.universe = MagicMock()
        cfg.universe.value = "paper"

        updates = ConfigUpdate(strategy="rsi")
        with patch("server.routers.config.configure_alerts"), \
             patch("server.routers.config.append_audit") as mock_audit:
            await update_config(updates=updates, cfg=cfg)

        call_args = mock_audit.call_args
        self.assertEqual(call_args[0][0], "paper")   # universe_val
        self.assertEqual(call_args[0][1], old_snap)  # old
        self.assertEqual(call_args[0][2], new_snap)  # new


if __name__ == "__main__":
    unittest.main()
