import unittest
from unittest.mock import AsyncMock

from server.events import WebsocketManager


class FakeWebSocket:
    def __init__(self, fail_send=False):
        self.accept = AsyncMock()
        self.send_json = AsyncMock()
        self.close = AsyncMock()
        if fail_send:
            self.send_json.side_effect = Exception("send fail")


class TestWebsocketManagerCoverage(unittest.IsolatedAsyncioTestCase):
    async def test_add_sends_cached_messages(self):
        manager = WebsocketManager()
        manager._last_status = {"event": "status", "value": 1}
        manager._last_signals = {"event": "signals", "value": 2}

        ws = FakeWebSocket()
        await manager.add(ws)

        ws.accept.assert_awaited_once()
        self.assertIn(ws, manager.connections)
        self.assertEqual(ws.send_json.await_count, 2)

    async def test_add_ignores_send_errors(self):
        manager = WebsocketManager()
        manager._last_status = {"event": "status"}

        ws = FakeWebSocket(fail_send=True)
        await manager.add(ws)
        ws.accept.assert_awaited_once()
        self.assertIn(ws, manager.connections)

    async def test_remove(self):
        manager = WebsocketManager()
        ws = FakeWebSocket()
        manager.connections.append(ws)

        await manager.remove(ws)
        self.assertNotIn(ws, manager.connections)

    async def test_broadcast_caches_and_drops_dead(self):
        manager = WebsocketManager()
        ws_ok = FakeWebSocket()
        ws_dead = FakeWebSocket(fail_send=True)
        manager.connections = [ws_ok, ws_dead]

        await manager.broadcast({"event": "status", "value": 1})

        self.assertEqual(manager._last_status, {"event": "status", "value": 1})
        self.assertIn(ws_ok, manager.connections)
        self.assertNotIn(ws_dead, manager.connections)
        ws_dead.close.assert_awaited()

    async def test_broadcast_close_errors_are_ignored(self):
        manager = WebsocketManager()
        ws_dead = FakeWebSocket(fail_send=True)
        ws_dead.close.side_effect = Exception("close fail")
        manager.connections = [ws_dead]

        await manager.broadcast({"event": "status", "value": 1})

        self.assertNotIn(ws_dead, manager.connections)

    async def test_broadcast_caches_signals(self):
        manager = WebsocketManager()
        await manager.broadcast({"event": "signals", "value": 2})
        self.assertEqual(manager._last_signals, {"event": "signals", "value": 2})


if __name__ == "__main__":
    unittest.main()
