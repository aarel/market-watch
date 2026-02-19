PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS requests (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  objective TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  archived_flag INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS status_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id TEXT NOT NULL,
  previous_status TEXT NOT NULL,
  new_status TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS verification_blocks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id TEXT NOT NULL UNIQUE,
  objectives_addressed TEXT NOT NULL,
  quality_checks TEXT NOT NULL,
  risks TEXT NOT NULL,
  final_status TEXT NOT NULL,
  FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  change_type TEXT NOT NULL,
  FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id TEXT NOT NULL,
  log_entry TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_requests_updated ON requests(updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_status_history_req ON status_history(request_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_req ON logs(request_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_artifacts_req ON artifacts(request_id);

CREATE TABLE IF NOT EXISTS runtime_input_pad (
  pad_key TEXT PRIMARY KEY,
  text_value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS communicate_reqs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  req_id TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  source TEXT NOT NULL,
  structured_payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_communicate_reqs_created ON communicate_reqs(created_at DESC, req_id DESC);
CREATE INDEX IF NOT EXISTS idx_communicate_reqs_source ON communicate_reqs(source, created_at DESC);
