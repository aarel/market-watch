# Observability

Market-Watch records structured JSONL event logs and evaluates agent behavior against expectations. This is a non-trading layer used for diagnostics and accountability.

## What gets logged

Each event on the EventBus is logged with:

- `timestamp`, `event_type`, `agent`
- `action`, `symbol`, `outcome`
- `reason` + `reason_code`
- `inputs`, `outputs`
- `context` (market open, symbol counts, volatility regime)

Logs are append-only JSONL at `logs/observability/agent_events.jsonl` by default.

## Evaluation

Run the evaluator to produce a JSON summary and a narrative report:

```bash
python -m monitoring \
  --log logs/observability/agent_events.jsonl \
  --output logs/observability/latest_eval.json \
  --report logs/observability/latest_report.txt
```

The server can also run evaluations on a schedule. Configure the interval using
`OBSERVABILITY_EVAL_INTERVAL_MINUTES` and read the latest summary from:

```
GET /api/observability
```

Run an on-demand evaluation:

```
POST /api/observability/evaluate
```

Fetch default expectations for display:

```
GET /api/observability/expectations
```

## Expectations

Defaults live in `monitoring/expectations.py`. You can override them with a JSON file:

```bash
python -c "from monitoring.expectations import dump_defaults; dump_defaults('monitoring/expectations.json')"
python -m monitoring --expectations monitoring/expectations.json
```

## Notes

- The evaluator does not change trading behavior.
- Context annotations are informational only (no external event attribution).
