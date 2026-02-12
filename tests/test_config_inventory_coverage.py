import importlib
import importlib.util
import sys
import types
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import scripts.config_inventory as ci


def test_module_inserts_repo_root():
    config_path = Path(__file__).resolve().parents[1] / "scripts" / "config_inventory.py"
    repo_root = config_path.parents[1]
    root_str = str(repo_root)

    original_sys_path = list(sys.path)
    try:
        sys.path[:] = [p for p in sys.path if p != root_str]
        importlib.reload(ci)
        assert root_str in sys.path
    finally:
        sys.path[:] = original_sys_path


def test_should_skip_file_branches(tmp_path):
    # Excluded extension
    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"x")
    assert ci._should_skip_file(image_path, exclude_dirs=set()) is True

    # Hidden file with no suffix
    hidden_path = tmp_path / ".env"
    hidden_path.write_text("SECRET=1")
    assert ci._should_skip_file(hidden_path, exclude_dirs=set()) is True

    # Oversized file
    big_path = tmp_path / "big.txt"
    big_path.write_text("xx")
    with patch("scripts.config_inventory.MAX_FILE_BYTES", 1):
        assert ci._should_skip_file(big_path, exclude_dirs=set()) is True

    # stat error
    missing_path = tmp_path / "missing.txt"
    assert ci._should_skip_file(missing_path, exclude_dirs=set()) is True

    # Excluded directory part
    excluded_dir = tmp_path / "logs"
    excluded_dir.mkdir()
    excluded_file = excluded_dir / "file.txt"
    excluded_file.write_text("data")
    assert ci._should_skip_file(excluded_file, exclude_dirs={"logs"}) is True

    # Not skipped
    normal_path = tmp_path / "ok.txt"
    normal_path.write_text("hello")
    assert ci._should_skip_file(normal_path, exclude_dirs=set()) is False


def test_read_text_branches(tmp_path):
    missing_path = tmp_path / "missing.txt"
    assert ci._read_text(missing_path) is None

    binary_path = tmp_path / "binary.bin"
    binary_path.write_bytes(b"a\x00b")
    assert ci._read_text(binary_path) is None

    text_path = tmp_path / "text.txt"
    text_path.write_text("hello")
    assert ci._read_text(text_path) == "hello"

    class BadBytes:
        def __contains__(self, item):
            return False

        def decode(self, *args, **kwargs):
            raise UnicodeError("boom")

    with patch("scripts.config_inventory.Path.read_bytes", return_value=BadBytes()):
        assert ci._read_text(text_path) is None


def test_scan_repo_counts_and_skips(tmp_path):
    file1 = tmp_path / "a.txt"
    file1.write_text("FOO BAR FOO")
    file2 = tmp_path / "b.txt"
    file2.write_text("BAR")
    file3 = tmp_path / "c.bin"
    file3.write_bytes(b"x\x00y")

    keys = ["FOO", "BAR"]
    stats = ci._scan_repo(tmp_path, keys, exclude_dirs=set())

    assert stats.scanned_files == 2
    assert stats.skipped_files == 1
    assert stats.key_counts["FOO"] == 2
    assert stats.key_counts["BAR"] == 2
    assert stats.key_files["FOO"][file1] == 2
    assert stats.key_files["BAR"][file1] == 1
    assert stats.key_files["BAR"][file2] == 1


def test_next_available_path(tmp_path):
    base = tmp_path / "report.md"
    assert ci._next_available_path(base) == base

    base.write_text("existing")
    second = tmp_path / "report_2.md"
    second.write_text("existing")
    expected = tmp_path / "report_3.md"
    assert ci._next_available_path(base) == expected


def test_render_report_includes_files_and_empty_sections(tmp_path):
    stats = ci.InventoryStats(
        scanned_files=1,
        skipped_files=0,
        key_counts={"FOO": 2, "BAR": 0},
        key_files={"FOO": {tmp_path / "a.py": 2}, "BAR": {}},
    )

    report = ci._render_report(
        stats=stats,
        repo_root=tmp_path,
        exclude_dirs={"logs"},
        generated_at=datetime(2024, 1, 1, tzinfo=UTC),
        keys=["FOO", "BAR"],
    )

    assert "Files: none" in report
    assert "`a.py` (2)" in report


def test_generate_config_inventory_writes_report(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "file.txt").write_text("FOO FOO")

    output_dir = tmp_path / "out"

    with patch("scripts.config_inventory.get_runtime_config_keys", return_value=["FOO"]):
        output_path, stats = ci.generate_config_inventory(
            repo_root=repo_root,
            output_dir=output_dir,
            exclude_dirs=set(),
        )

    assert output_path.exists()
    assert stats.scanned_files == 1
    assert stats.key_counts["FOO"] == 2


def test_main_parses_args_and_calls_generator(tmp_path):
    dummy_stats = ci.InventoryStats(
        scanned_files=1,
        skipped_files=0,
        key_counts={"FOO": 1},
        key_files={"FOO": {Path("x"): 1}},
    )

    with patch("scripts.config_inventory.generate_config_inventory", return_value=(tmp_path / "out.md", dummy_stats)):
        with patch("builtins.print") as mocked_print:
            argv = [
                "config_inventory.py",
                "--repo",
                str(tmp_path),
                "--output-dir",
                str(tmp_path / "reports"),
                "--exclude-dirs",
                "foo,bar",
            ]
            with patch.object(sys, "argv", argv):
                result = ci.main()

    assert result == 0
    assert mocked_print.called
