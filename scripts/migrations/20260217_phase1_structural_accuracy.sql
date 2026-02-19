-- Phase 1 Structural Accuracy Layer (non-breaking extension)
-- Adds optional trade-level accounting columns and new domain tables.

ALTER TABLE trades ADD COLUMN lot_id TEXT NULL;
ALTER TABLE trades ADD COLUMN realized_gain REAL NULL;
ALTER TABLE trades ADD COLUMN settlement_date TEXT NULL;
ALTER TABLE trades ADD COLUMN corporate_action_flag INTEGER NULL;

CREATE TABLE IF NOT EXISTS corporate_actions (
    event_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    action_type TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    ratio REAL NULL,
    cash_amount REAL NULL,
    metadata_json TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lots (
    lot_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL,
    entry_price REAL NOT NULL,
    entry_date TEXT NOT NULL,
    remaining_quantity REAL NOT NULL,
    adjusted_cost_basis REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
