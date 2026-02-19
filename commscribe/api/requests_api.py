"""SQLite-only request API layer for communicate UI compatibility."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any

from commscribe.engine.communicate_db import CommunicateDB

def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _extract_title_objective(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    title = ""
    objective = ""
    for i, raw in enumerate(lines):
        s = raw.strip()
        u = s.upper()
        if u in {"TITLE", "TITLE:"}:
            for nxt in lines[i + 1 :]:
                if nxt.strip():
                    title = nxt.strip()
                    break
        if u in {"OBJECTIVE", "OBJECTIVE:"}:
            cap = []
            for nxt in lines[i + 1 :]:
                t = nxt.strip()
                if not t:
                    break
                if re.fullmatch(r"[A-Z][A-Z0-9 _:-]+", t):
                    break
                cap.append(t)
            objective = " ".join(cap).strip()
            break
    if not title:
        for line in lines:
            if line.strip():
                title = line.strip()
                break
    if not objective:
        objective = title or "No objective"
    return title[:200], objective[:500]


def _next_req_id(existing_ids: set[str]) -> str:
    base = dt.datetime.now().strftime("REQ-%Y%m%d-%H%M%S")
    if base not in existing_ids:
        return base
    i = 2
    while f"{base}-{i}" in existing_ids:
        i += 1
    return f"{base}-{i}"


class SQLiteRequestStore:
    def __init__(self, db_path: str | Path, schema_path: str | Path):
        self.db = CommunicateDB(db_path)
        self.db.init_schema(schema_path)

    def get_all_requests(
        self,
        include_archived: bool = False,
        created_date: str | None = None,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT r.* FROM requests r WHERE 1=1"
        params: list[Any] = []
        if not include_archived:
            query += " AND r.archived_flag = 0"
        if created_date:
            query += " AND date(r.created_at) = ?"
            params.append(created_date)
        if source == "communicate>":
            query += (
                " AND (EXISTS (SELECT 1 FROM communicate_reqs c WHERE c.req_id = r.id AND c.source = ?)"
                " OR EXISTS (SELECT 1 FROM logs l WHERE l.request_id = r.id AND l.log_entry LIKE 'REQUEST_TEXT::%'))"
            )
            params.append(source)
        query += " ORDER BY datetime(r.updated_at) DESC, r.id DESC"
        with self.db._connect() as conn:  # noqa: SLF001
            rows = conn.execute(query, tuple(params)).fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "id": r["id"],
                    "title": r["title"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "archived_flag": bool(r["archived_flag"]),
                }
            )
        return out

    def get_request(self, request_id: str) -> dict[str, Any] | None:
        try:
            row = self.db.get_request(request_id)
        except ValueError:
            return None
        artifacts: list[dict[str, str]] = []
        logs: list[dict[str, str]] = []
        verification = self.get_verification_block(request_id)

        request_text = ""
        codex_ack_plan_lines: list[str] = []
        execution_log_lines: list[str] = []
        outputs_lines: list[str] = []
        evidence_lines: list[str] = []

        with self.db._connect() as conn:  # noqa: SLF001
            for a in conn.execute("SELECT file_path, change_type FROM artifacts WHERE request_id = ?", (request_id,)).fetchall():
                artifacts.append({"file_path": a["file_path"], "change_type": a["change_type"]})
            for l in conn.execute("SELECT log_entry, timestamp FROM logs WHERE request_id = ? ORDER BY id ASC", (request_id,)).fetchall():
                entry = l["log_entry"]
                logs.append({"log_entry": entry, "timestamp": l["timestamp"]})
                if entry.startswith("REQUEST_TEXT::"):
                    request_text = entry.removeprefix("REQUEST_TEXT::").strip()
                elif entry.startswith("ACK_PLAN::"):
                    codex_ack_plan_lines.append(entry.removeprefix("ACK_PLAN::").strip())
                elif entry.startswith("RESULT::"):
                    outputs_lines.append(entry.removeprefix("RESULT::").strip())
                elif entry.startswith("EVIDENCE::"):
                    evidence_lines.append(entry.removeprefix("EVIDENCE::").strip())
                elif not entry.startswith(("BLOCKED::", "NEXT_STEPS::")):
                    execution_log_lines.append(entry)

        return {
            "id": row["id"],
            "title": row["title"],
            "objective": row["objective"],
            "status": row["status"],
            "request_text": request_text,
            "codex_ack_plan": "\n".join(line for line in codex_ack_plan_lines if line).strip(),
            "execution_log": "\n".join(line for line in execution_log_lines if line).strip(),
            "outputs": "\n".join(line for line in outputs_lines if line).strip(),
            "evidence": "\n".join(line for line in evidence_lines if line).strip(),
            "artifacts": artifacts,
            "verification": verification,
            "logs": logs,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "archived_flag": bool(row["archived_flag"]),
        }

    def create_request(self, text: str) -> str:
        title, objective = _extract_title_objective(text)
        existing = {r["id"] for r in self.db.list_requests()}
        rid = _next_req_id(existing)
        self.db.create_request(rid, title, objective, status="INPUT_PAD")
        self.db.transition_status(rid, "IN_PROGRESS")
        self.db.add_log(rid, f"created_from_ui { _now_iso() }")
        with self.db._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT created_at, updated_at FROM requests WHERE id = ?",
                (rid,),
            ).fetchone()
            if row is not None:
                conn.execute(
                    """
                    INSERT INTO communicate_reqs(req_id, title, status, created_at, updated_at, source, structured_payload)
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(req_id) DO UPDATE SET
                      title=excluded.title,
                      status=excluded.status,
                      updated_at=excluded.updated_at,
                      source=excluded.source,
                      structured_payload=excluded.structured_payload
                    """,
                    (rid, title, "IN_PROGRESS", row["created_at"], row["updated_at"], "ui", text.strip()),
                )
                conn.commit()
        return rid

    def update_request(self, request_id: str, status: str | None = None, log_entry: str | None = None) -> None:
        if status:
            self.db.transition_status(request_id, status)
        if log_entry:
            self.db.add_log(request_id, log_entry)

    def complete_request(self, request_id: str, verification: dict[str, str]) -> None:
        self.db.complete_with_verification(
            request_id,
            objectives_addressed=verification.get("objectives_addressed", ""),
            quality_checks=verification.get("quality_checks", ""),
            risks=verification.get("risks", ""),
            final_status=verification.get("final_status", ""),
        )

    def set_archived(self, request_id: str, archived_flag: bool) -> None:
        with self.db._connect() as conn:  # noqa: SLF001
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE requests SET archived_flag = ?, updated_at = ? WHERE id = ?",
                (1 if archived_flag else 0, _now_iso(), request_id),
            )
            conn.commit()

    def get_verification_block(self, request_id: str) -> dict[str, Any] | None:
        with self.db._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT objectives_addressed, quality_checks, risks, final_status FROM verification_blocks WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "objectives_addressed": row["objectives_addressed"],
            "quality_checks": row["quality_checks"],
            "risks": row["risks"],
            "final_status": row["final_status"],
        }

    def export_markdown(self) -> str:
        return self.db.export_markdown()

    def get_input_pad(self) -> str:
        with self.db._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT text_value FROM runtime_input_pad WHERE pad_key = ?",
                ("input_pad",),
            ).fetchone()
        if row is None:
            return ""
        return str(row["text_value"] or "")

    def set_input_pad(self, text: str) -> None:
        with self.db._connect() as conn:  # noqa: SLF001
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO runtime_input_pad(pad_key, text_value, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(pad_key) DO UPDATE SET
                  text_value=excluded.text_value,
                  updated_at=excluded.updated_at
                """,
                ("input_pad", text.strip(), _now_iso()),
            )
            conn.commit()


class RequestAPI:
    def __init__(self, db_path: str | Path, schema_path: str | Path):
        self.backend = "sqlite"
        self.db_path = Path(db_path)
        self.schema_path = Path(schema_path)
        self.store = SQLiteRequestStore(self.db_path, self.schema_path)

    @classmethod
    def from_env_or_args(
        cls,
        json_file: str | Path,
        db_path: str | Path,
        schema_path: str | Path,
        backend: str | None = None,
    ) -> "RequestAPI":
        del json_file
        if backend and backend != "sqlite":
            raise ValueError("Only sqlite backend is supported")
        return cls(db_path=db_path, schema_path=schema_path)

    def get_all_requests(
        self,
        include_archived: bool = False,
        created_date: str | None = None,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.store.get_all_requests(
            include_archived=include_archived,
            created_date=created_date,
            source=source,
        )

    def get_request(self, request_id: str) -> dict[str, Any] | None:
        return self.store.get_request(request_id)

    def create_request(self, text: str) -> str:
        return self.store.create_request(text)

    def update_request(self, request_id: str, status: str | None = None, log_entry: str | None = None) -> None:
        self.store.update_request(request_id, status=status, log_entry=log_entry)

    def complete_request(self, request_id: str, verification: dict[str, str]) -> None:
        self.store.complete_request(request_id, verification)

    def get_verification_block(self, request_id: str) -> dict[str, Any] | None:
        return self.store.get_verification_block(request_id)

    def export_markdown(self) -> str:
        return self.store.export_markdown()

    def get_input_pad(self) -> str:
        return self.store.get_input_pad()

    def set_input_pad(self, text: str) -> None:
        self.store.set_input_pad(text)
