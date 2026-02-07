# Observability

Market-Watch records structured JSONL event logs for all agent activity. This is a non-trading layer used for diagnostics, monitoring, and accountability.

## What Gets Logged

The `ObservabilityAgent` subscribes to all EventBus events and writes structured logs with:

- `timestamp`, `event_type`, `agent`
- `action`, `symbol`, `outcome` (ok/warn/fail)
- `reason` + `reason_code`
- `inputs`, `outputs`
- `context` (market open, symbol counts, volatility regime)

**Log Location:** `logs/{universe}/system/agent_events.jsonl`
- Universe-scoped (separate logs for LIVE, PAPER, SIMULATION)
- Append-only JSONL format
- Auto-rotates when exceeds max size (default 5MB)

## Event Classification

Events are classified into three outcome levels:

- **ok**: Normal operation (signal generated, risk check passed, order executed)
- **warn**: Attention needed but not critical (risk limit approached, signal filtered)
- **fail**: Error or rejection (risk check failed, order rejected, stop loss triggered)

Classification is automatic via `monitoring/reason_codes.py`.

## API Endpoints

### Get Today's Warn/Fail Logs

```
GET /observability/logs?level=warn
```

**Returns:** All warn and fail events from today (filtered by NY EST timezone)

**Also writes:** Daily CSV to `logs/risk-and-obs-alerts/YYYYMMDD_risk_obs.csv` (overwrites on each request)

**Query Parameters:**
- `level`: Filter level (default "warn", only warn/fail events returned regardless)

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2026-02-05T14:30:00",
      "agent": "RiskAgent",
      "event_type": "RiskCheckFailed",
      "outcome": "fail",
      "reason": "Daily loss limit exceeded",
      "reason_code": "daily_loss_limit",
      "symbol": "AAPL",
      "action": "buy"
    }
  ]
}
```

## Daily CSV Export

On each `/observability/logs` request, a CSV file is written to:
- **Path:** `logs/risk-and-obs-alerts/YYYYMMDD_risk_obs.csv`
- **Filename rotates:** At midnight EST (e.g., `20260205_risk_obs.csv`)
- **Overwrites:** Each request overwrites the file with latest today's data
- **Fields:** timestamp, agent, event_type, action, symbol, outcome, reason

This provides a persistent daily snapshot of warn/fail events.

## Anomaly Alerts

When alerting is enabled, detected anomaly spikes trigger external alerts via the AlertManager (email/webhook). This wiring is handled inside `ObservabilityAgent` and uses the same alert configuration as Phase C.

## Configuration

**Environment Variables:**
- `OBSERVABILITY_LOG_PATH`: Log file path (default: `logs/system/agent_events.jsonl`)
- `OBSERVABILITY_MAX_LOG_MB`: Max log size before rotation (default: 5)

**Note:** Observability path is auto-scoped by universe via `SystemLogWriter`, so the actual path will be `logs/{universe}/system/agent_events.jsonl`.

## Implementation

**ObservabilityAgent:** `agents/observability_agent.py`
- Subscribes to all events via `event_bus.subscribe_all()`
- Classifies event outcomes using `monitoring/reason_codes.classify_event()`
- Writes structured logs via `monitoring/logger.SystemLogWriter`

**API Router:** `server/routers/observability.py`
- Filters logs by date (today only, NY EST)
- Returns warn/fail events for UI display
- Writes daily CSV export

## Notes

- Observability does not affect trading behavior (read-only monitoring)
- Universe-scoped logs prevent cross-contamination between LIVE/PAPER/SIMULATION
- Logs are append-only (never modified, only rotated when size limit reached)
- Context annotations are informational (no external event attribution)
