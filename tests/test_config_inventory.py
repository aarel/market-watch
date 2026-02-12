from pathlib import Path

from scripts import config_inventory


def test_config_inventory_generates_report(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    output_path, stats = config_inventory.generate_config_inventory(
        repo_root=repo_root,
        output_dir=tmp_path,
    )
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "Config Inventory Report" in content
    assert stats.scanned_files >= 1
    keys = config_inventory.get_runtime_config_keys()
    assert all(key in content for key in keys)
