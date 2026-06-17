import asyncio
import base64
import json
import threading
from dataclasses import fields, is_dataclass
from typing import Any


class SnapshotServer:
    """Non-blocking WebSocket publisher for executor state."""

    def __init__(self, host: str, port: int) -> None:
        """Configure a daemon thread that will own the asyncio server loop."""

        self.host = host
        self.port = port
        self.clients: set[Any] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.stop_event: asyncio.Event | None = None
        self.thread = threading.Thread(target=self.run, name="executor-ws", daemon=True)

    def start(self) -> None:
        """Start the ws server thread without waiting for clients."""

        self.thread.start()

    def publish(self, payload: dict[str, Any]) -> None:
        """Schedule a best-effort broadcast without blocking the caller."""

        if self.loop is None or self.loop.is_closed():
            return
        try:
            self.loop.call_soon_threadsafe(asyncio.create_task, self.broadcast(payload))
        except RuntimeError:
            return

    def stop(self) -> None:
        """Ask the server loop to stop and wait briefly for the thread."""

        if self.loop is not None and self.stop_event is not None:
            self.loop.call_soon_threadsafe(self.stop_event.set)
        if self.thread.is_alive():
            self.thread.join(timeout=2)

    def run(self) -> None:
        """Thread target for running the asyncio websocket server."""

        asyncio.run(self.serve())

    async def serve(self) -> None:
        """Accept clients and keep the server alive until stop is requested."""

        import websockets

        self.loop = asyncio.get_running_loop()
        self.stop_event = asyncio.Event()

        async def handler(websocket: Any) -> None:
            """Keep one websocket client registered until the server stops."""

            self.clients.add(websocket)
            try:
                await self.stop_event.wait()
            finally:
                self.clients.discard(websocket)

        async with websockets.serve(handler, self.host, self.port):
            await self.stop_event.wait()

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Send a payload to connected clients and drop stale connections."""

        if not self.clients:
            return
        message = json.dumps(self.clean(payload), ensure_ascii=True)
        stale = []
        for client in tuple(self.clients):
            try:
                await asyncio.wait_for(client.send(message), timeout=0.01)
            except Exception:
                stale.append(client)
        for client in stale:
            self.clients.discard(client)

    def clean(self, value: Any) -> Any:
        """Convert dataclasses, numpy arrays, and bytes into JSON values."""

        if is_dataclass(value) and not isinstance(value, type):
            return {field.name: self.clean(getattr(value, field.name)) for field in fields(value)}
        if isinstance(value, dict):
            return {str(key): self.clean(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.clean(item) for item in value]
        if isinstance(value, bytes):
            return base64.b64encode(value).decode("ascii")
        if hasattr(value, "tolist"):
            return value.tolist()
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return repr(value)
