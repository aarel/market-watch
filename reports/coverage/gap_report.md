# Coverage Gap Report

- Overall line coverage: 79.63%
- Overall branch coverage: 69.75%

## Critical Modules

| Module | Line % | Line Target | Branch % | Branch Target |
|---|---:|---:|---:|---:|
| server/ | 67.00 | 72.00 | 43.60 | 55.00 |
| scripts/governance/ | n/a | 80.00 | n/a | 70.00 |
| commscribe/scripts/ | n/a | 80.00 | n/a | 70.00 |

## Top 20 Files by Missed Lines

| File | Missed Lines | Line % | Missed Branches | Branch % |
|---|---:|---:|---:|---:|
| fake_broker.py | 150 | 23.44 | 59 | 10.61 |
| backtest/data.py | 121 | 16.13 | 61 | 1.61 |
| broker.py | 98 | 29.89 | 24 | 20.00 |
| server/routers/analytics.py | 87 | 28.39 | 24 | 7.69 |
| backtest/cli.py | 59 | 30.15 | 36 | 5.26 |
| server/routers/trading.py | 55 | 21.00 | 24 | 0.00 |
| server/lifespan.py | 54 | 18.60 | 16 | 0.00 |
| server/routers/observability.py | 40 | 28.77 | 12 | 0.00 |
| monitoring/evaluator.py | 37 | 60.28 | 19 | 40.62 |
| alerts/runtime.py | 31 | 51.02 | 17 | 22.73 |
| backtest/results.py | 29 | 67.59 | 6 | 57.14 |
| analytics/store.py | 20 | 85.48 | 16 | 80.00 |
| agents/replay_recorder_agent.py | 15 | 72.62 | 8 | 55.56 |
| risk/exposure_checkers.py | 15 | 90.05 | 7 | 88.33 |
| monitoring/reason_codes.py | 14 | 66.27 | 14 | 63.16 |
| analytics/metrics.py | 14 | 93.07 | 9 | 89.77 |
| server/routers/status.py | 14 | 73.75 | 7 | 50.00 |
| agents/monitor_agent.py | 13 | 67.80 | 6 | 40.00 |
| agents/session_logger_agent.py | 12 | 65.96 | 4 | 33.33 |
| scripts/run_test_audit.py | 10 | 69.84 | 9 | 50.00 |
