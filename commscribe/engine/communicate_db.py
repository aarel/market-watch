"""SQLite-backed communication engine for deterministic REQ lifecycle management."""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import Iterable

from .state_machine import assert_transition


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


class CommunicateDB:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_schema(self, schema_path: str | Path) -> None:
        schema = Path(schema_path).read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.executescript(schema)
            conn.commit()

    def create_request(
        self,
        request_id: str,
        title: str,
        objective: str,
        status: str = "INPUT_PAD",
        artifacts: Iterable[tuple[str, str]] | None = None,
    ) -> None:
        ts = _now_iso()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO requests(id, title, objective, status, created_at, updated_at, archived_flag)
                VALUES(?, ?, ?, ?, ?, ?, 0)
                """,
                (request_id, title.strip(), objective.strip(), status.upper(), ts, ts),
            )
            if artifacts:
                conn.executemany(
                    "INSERT INTO artifacts(request_id, file_path, change_type) VALUES(?, ?, ?)",
                    [(request_id, p, t) for p, t in artifacts],
                )
            conn.commit()

    def insert_migrated_request(
        self,
        request_id: str,
        title: str,
        objective: str,
        status: str,
        created_at: str,
        updated_at: str,
        archived_flag: int = 0,
    ) -> None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT OR REPLACE INTO requests(id, title, objective, status, created_at, updated_at, archived_flag)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (request_id, title.strip(), objective.strip(), status.upper(), created_at, updated_at, int(archived_flag)),
            )
            conn.commit()

    def get_request(self, request_id: str) -> sqlite3.Row:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown request id: {request_id}")
        return row

    def list_requests(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM requests ORDER BY datetime(updated_at) DESC, id DESC"
            ).fetchall()
        return list(rows)

    def transition_status(self, request_id: str, new_status: str) -> None:
        new = new_status.upper()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute("SELECT status FROM requests WHERE id = ?", (request_id,)).fetchone()
            if cur is None:
                raise ValueError(f"Unknown request id: {request_id}")
            prev = cur["status"].upper()
            assert_transition(prev, new)
            if new == "DONE":
                v = conn.execute(
                    "SELECT 1 FROM verification_blocks WHERE request_id = ?", (request_id,)
                ).fetchone()
                if v is None:
                    raise ValueError("DONE requires verification_blocks row")
            ts = _now_iso()
            conn.execute(
                "UPDATE requests SET status = ?, updated_at = ? WHERE id = ?",
                (new, ts, request_id),
            )
            conn.execute(
                "INSERT INTO status_history(request_id, previous_status, new_status, timestamp) VALUES(?, ?, ?, ?)",
                (request_id, prev, new, ts),
            )
            conn.commit()

    def add_log(self, request_id: str, entry: str) -> None:
        ts = _now_iso()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM requests WHERE id = ?", (request_id,)).fetchone() is None:
                raise ValueError(f"Unknown request id: {request_id}")
            conn.execute(
                "INSERT INTO logs(request_id, log_entry, timestamp) VALUES(?, ?, ?)",
                (request_id, entry.strip(), ts),
            )
            conn.execute("UPDATE requests SET updated_at = ? WHERE id = ?", (ts, request_id))
            conn.commit()

    def add_artifact(self, request_id: str, file_path: str, change_type: str) -> None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM requests WHERE id = ?", (request_id,)).fetchone() is None:
                raise ValueError(f"Unknown request id: {request_id}")
            conn.execute(
                "INSERT INTO artifacts(request_id, file_path, change_type) VALUES(?, ?, ?)",
                (request_id, file_path, change_type),
            )
            conn.commit()

    def upsert_verification_block(
        self,
        request_id: str,
        objectives_addressed: str,
        quality_checks: str,
        risks: str,
        final_status: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM requests WHERE id = ?", (request_id,)).fetchone() is None:
                raise ValueError(f"Unknown request id: {request_id}")
            conn.execute(
                """
                INSERT INTO verification_blocks(request_id, objectives_addressed, quality_checks, risks, final_status)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(request_id) DO UPDATE SET
                  objectives_addressed=excluded.objectives_addressed,
                  quality_checks=excluded.quality_checks,
                  risks=excluded.risks,
                  final_status=excluded.final_status
                """,
                (
                    request_id,
                    objectives_addressed.strip(),
                    quality_checks.strip(),
                    risks.strip(),
                    final_status.strip(),
                ),
            )
            conn.commit()

    def complete_with_verification(
        self,
        request_id: str,
        objectives_addressed: str,
        quality_checks: str,
        risks: str,
        final_status: str,
    ) -> None:
        self.upsert_verification_block(request_id, objectives_addressed, quality_checks, risks, final_status)
        self.transition_status(request_id, "DONE")

    def export_markdown(self) -> str:
        rows = self.list_requests()
        lines = ["# Communicate Export", ""]
        for row in rows:
            lines.append(f"## REQUEST {row['id']}")
            lines.append(f"- TITLE: {row['title']}")
            lines.append(f"- OBJECTIVE: {row['objective']}")
            lines.append(f"- STATUS: {row['status']}")
            lines.append(f"- CREATED_AT: {row['created_at']}")
            lines.append(f"- UPDATED_AT: {row['updated_at']}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"
