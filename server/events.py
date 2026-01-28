"""Broadcast helpers and websocket registry."""
from typing import List

from fastapi import WebSocket


class WebsocketManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def add(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    async def remove(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict):
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
