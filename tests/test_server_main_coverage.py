import unittest
from unittest.mock import AsyncMock, patch

from server import main as server_main


class TestServerMainCoverage(unittest.IsolatedAsyncioTestCase):
    async def test_noop_lifespan_yields(self):
        async with server_main.noop_lifespan(None):
            self.assertTrue(True)

    async def test_websocket_endpoint_adds_and_removes(self):
        class FakeWebSocket:
            def __init__(self):
                self._calls = 0

            async def receive_text(self):
                self._calls += 1
                raise RuntimeError("disconnect")

        websocket = FakeWebSocket()

        with patch.object(server_main, "ws_manager") as manager:
            manager.add = AsyncMock()
            manager.remove = AsyncMock()

            await server_main.websocket_endpoint(websocket)

            manager.add.assert_awaited_once_with(websocket)
            manager.remove.assert_awaited_once_with(websocket)


if __name__ == "__main__":
    unittest.main()
