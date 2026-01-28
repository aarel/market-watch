Replay data format
==================

We store per-symbol intraday bars as CSV for offline/SIM replay.

Path: `data/replay/<symbol>-<YYYYMMDD>.csv`

Columns:
`timestamp,open,high,low,close,volume`

Times are ISO (UTC). One row per bar (e.g., 1-minute bars).

Workflow:
1) During market hours, record bars with the ReplayRecorder utility (see scripts/replay_recorder.py).
2) After hours (SIM), FakeBroker can load and replay these bars instead of random walk.
