"""Broadcast helpers and websocket registry."""

from fastapi import WebSocket


class WebsocketManager:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self._last_status: dict | None = None
        self._last_signals: dict | None = None

    async def add(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
        # Push cached state so new connections see data immediately rather than
        # waiting up to TRADE_INTERVAL_MINUTES for the next broadcast.
        try:
            if self._last_status:
                await ws.send_json(self._last_status)
            if self._last_signals:
                await ws.send_json(self._last_signals)
        except Exception:
            pass

    async def remove(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict):
        # Cache status and signals so new connections can catch up.
        event = message.get("event")
        if event == "status":
            self._last_status = message
        elif event == "signals":
            self._last_signals = message

        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            try:
                await ws.close()
            except Exception:
                pass
            if ws in self.connections:
                self.connections.remove(ws)
