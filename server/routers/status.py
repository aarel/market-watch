from datetime import datetime, timezone
import os
import psutil

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from ..dependencies import get_state
from ..events import WebsocketManager

router = APIRouter()


@router.get("/health")
async def health(state=Depends(get_state)):
    now = datetime.now(timezone.utc)
    start_time = state.start_time
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    uptime_seconds = (now - start_time).total_seconds()

    # Application check
    application_status = "ok"
    if getattr(state, "error", None):
        application_status = "degraded"

    # Agents check
    agents_status = "fail"
    if state.coordinator:
        agent_status = state.coordinator.status()
        down = any(not info.get("running", True) for info in agent_status["agents"].values())
        agents_status = "degraded" if down else "ok"
    else:
        agents_status = "fail"

    # Broker check
    broker_status = "ok" if state.broker else "fail"

    # File system check (basic writeability)
    fs_status = "ok"
    try:
        tmp_path = ".healthcheck.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(tmp_path)
    except Exception:
        fs_status = "fail"

    # Memory check
    try:
        process = psutil.Process()
        mem_info = process.memory_info()
        mem_mb = mem_info.rss / (1024 * 1024)
        mem_percent = psutil.virtual_memory().percent
        memory = {"status": "ok", "usage_mb": round(mem_mb, 2), "usage_percent": mem_percent, "message": "memory usage"}
    except Exception:
        memory = {"status": "degraded", "message": "memory check failed"}

    checks = {
        "application": {"status": application_status, "message": "app running"},
        "agents": {"status": agents_status, "message": "agent status check"},
        "broker_api": {"status": broker_status, "message": "broker connectivity"},
        "file_system": {"status": fs_status, "message": "fs writable"},
        "memory": memory,
    }

    overall = "healthy"
    if "fail" in {c["status"] for c in checks.values()}:
        overall = "unhealthy"
    elif "degraded" in {c["status"] for c in checks.values()}:
        overall = "unhealthy"  # keep simple for tests

    payload = {
        "status": overall,
        "timestamp": now.isoformat(),
        "uptime_seconds": uptime_seconds,
        "checks": checks,
    }
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE if overall == "unhealthy" else status.HTTP_200_OK
    return JSONResponse(content=payload, status_code=status_code)


@router.get("/status")
async def get_status(state=Depends(get_state)):
    if not state.coordinator:
        return {"running": False}
    agent_status = state.coordinator.status()
    return {"running": True, "agents": agent_status}
