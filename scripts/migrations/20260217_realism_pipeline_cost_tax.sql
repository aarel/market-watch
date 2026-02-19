-- Realism runtime integration extensions for cost/tax outputs (non-breaking)

ALTER TABLE trades ADD COLUMN gross_pnl REAL NULL;
ALTER TABLE trades ADD COLUMN net_pnl REAL NULL;
ALTER TABLE trades ADD COLUMN after_tax_pnl REAL NULL;
ALTER TABLE trades ADD COLUMN tax_estimate REAL NULL;
ALTER TABLE trades ADD COLUMN fees_total REAL NULL;
ALTER TABLE trades ADD COLUMN fee_breakdown_json TEXT NULL;
ALTER TABLE trades ADD COLUMN realism_pipeline_enabled INTEGER NULL;

-- Tier B placeholders for forward compatibility
ALTER TABLE trades ADD COLUMN margin_interest REAL NULL;
ALTER TABLE trades ADD COLUMN fx_rate_used REAL NULL;
