#!/usr/bin/env python3
"""
Migrate existing data files to universe-scoped directory structure.

This script moves pre-universe-isolation data into the appropriate
universe-scoped directories. Since we can't determine which universe
the old data came from, we migrate it to SIMULATION by default (safest).
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

# Project root
ROOT = Path(__file__).resolve().parents[1]

def backup_existing_data():
    """Create backup of existing data before migration."""
    backup_dir = ROOT / "data" / "pre_migration_backup"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"backup_{timestamp}"
    backup_path.mkdir(exist_ok=True)
    
    print(f"Creating backup at: {backup_path}")
    
    # Backup analytics data
    analytics_dir = ROOT / "data" / "analytics"
    if analytics_dir.exists():
        shutil.copytree(analytics_dir, backup_path / "analytics")
        print(f"  ✓ Backed up analytics/")
    
    # Backup config_state.json
    config_file = ROOT / "data" / "config_state.json"
    if config_file.exists():
        shutil.copy(config_file, backup_path / "config_state.json")
        print(f"  ✓ Backed up config_state.json")
    
    return backup_path

def migrate_analytics_to_simulation():
    """Migrate analytics data to simulation universe."""
    analytics_dir = ROOT / "data" / "analytics"
    sim_dir = ROOT / "data" / "simulation"
    
    if not analytics_dir.exists():
        print("No analytics directory found, skipping.")
        return
    
    print("\nMigrating analytics data to simulation universe...")
    
    # Move equity.jsonl
    equity_src = analytics_dir / "equity.jsonl"
    equity_dst = sim_dir / "equity.jsonl"
    if equity_src.exists():
        shutil.move(str(equity_src), str(equity_dst))
        print(f"  ✓ Moved equity.jsonl → data/simulation/")
    
    # Move trades.jsonl
    trades_src = analytics_dir / "trades.jsonl"
    trades_dst = sim_dir / "trades.jsonl"
    if trades_src.exists():
        shutil.move(str(trades_src), str(trades_dst))
        print(f"  ✓ Moved trades.jsonl → data/simulation/")
    
    # Remove empty analytics directory
    if analytics_dir.exists() and not any(analytics_dir.iterdir()):
        analytics_dir.rmdir()
        print(f"  ✓ Removed empty analytics/ directory")

def migrate_config_to_simulation():
    """Copy config_state.json to simulation universe (keep original for now)."""
    config_src = ROOT / "data" / "config_state.json"
    config_dst = ROOT / "data" / "simulation" / "config.json"
    
    if not config_src.exists():
        print("\nNo config_state.json found, skipping.")
        return
    
    print("\nCopying config to simulation universe...")
    shutil.copy(str(config_src), str(config_dst))
    print(f"  ✓ Copied config_state.json → data/simulation/config.json")
    print(f"  ℹ Original config_state.json kept for reference (will be removed in Week 2)")

def create_empty_configs():
    """Create empty config files for live and paper universes."""
    print("\nCreating empty config files for live and paper...")
    
    default_config = {
        "note": "This config will be populated when you first run in this universe",
        "created": datetime.now().isoformat()
    }
    
    for universe in ["live", "paper"]:
        config_path = ROOT / "data" / universe / "config.json"
        if not config_path.exists():
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"  ✓ Created {universe}/config.json")

def verify_migration():
    """Verify migration was successful."""
    print("\nVerifying migration...")
    
    errors = []
    
    # Check simulation has equity and trades
    sim_dir = ROOT / "data" / "simulation"
    if not (sim_dir / "equity.jsonl").exists():
        errors.append("Missing data/simulation/equity.jsonl")
    if not (sim_dir / "trades.jsonl").exists():
        errors.append("Missing data/simulation/trades.jsonl")
    if not (sim_dir / "config.json").exists():
        errors.append("Missing data/simulation/config.json")
    
    # Check shared data exists
    shared_dir = ROOT / "data" / "shared"
    if not (shared_dir / "sector_map.json").exists():
        errors.append("Missing data/shared/sector_map.json")
    if not (shared_dir / "historical").exists():
        errors.append("Missing data/shared/historical/")
    
    if errors:
        print("  ❌ Errors found:")
        for error in errors:
            print(f"     - {error}")
        return False
    else:
        print("  ✓ All expected files present")
        return True

def print_summary():
    """Print summary of new directory structure."""
    print("\n" + "="*60)
    print("Migration Complete!")
    print("="*60)
    print("\nNew directory structure:")
    print("""
data/
├── live/           # Real capital trading (empty, ready for use)
├── paper/          # Paper trading (empty, ready for use)
├── simulation/     # Your existing data migrated here
│   ├── config.json
│   ├── equity.jsonl
│   └── trades.jsonl
└── shared/         # Universe-agnostic data
    ├── historical/
    ├── sector_map.json
    └── replay/

logs/
├── live/           # Live trading logs (empty)
├── paper/          # Paper trading logs (empty)
├── simulation/     # Simulation logs (new logs will go here)
└── system/         # System logs (tests, ui_checks)
    """)
    
    print("\nNext Steps:")
    print("  1. Run tests to ensure nothing broke: python -m pytest tests/")
    print("  2. Update code to use universe-scoped paths (Week 1 continues)")
    print("  3. Old config_state.json will be removed in Week 2")

def main():
    """Run migration."""
    print("="*60)
    print("Data Namespace Migration")
    print("="*60)
    print("\nThis script migrates existing data to universe-scoped directories.")
    print("Your data will be moved to the SIMULATION universe (safest default).")
    
    # Create backup
    backup_path = backup_existing_data()
    
    try:
        # Migrate data
        migrate_analytics_to_simulation()
        migrate_config_to_simulation()
        create_empty_configs()
        
        # Verify
        if verify_migration():
            print_summary()
        else:
            print("\n❌ Migration verification failed!")
            print(f"   Backup available at: {backup_path}")
            return 1
    
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"   Backup available at: {backup_path}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
