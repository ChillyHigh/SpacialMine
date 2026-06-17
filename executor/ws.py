import asyncio
import base64
import json
import logging
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

    def publish(self, payload: dict[str, Any], image: Any = None) -> None:
        """Schedule a best-effort broadcast without blocking the caller."""

        if self.loop is None or self.loop.is_closed():
            return
        try:
            self.loop.call_soon_threadsafe(lambda: asyncio.create_task(self.broadcast(payload, image)))
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

    async def broadcast(self, payload: dict[str, Any], image: Any = None) -> None:
        """Send a payload to connected clients and drop stale connections."""

        if not self.clients:
            return
        try:
            message_payload = self.clean(payload)
            if image is not None:
                import cv2

                frame = image
                if hasattr(frame, "dtype") and str(frame.dtype) != "uint8":
                    frame = frame.astype("uint8")
                if hasattr(frame, "ndim") and frame.ndim == 3 and frame.shape[2] == 3:
                    frame = frame[:, :, ::-1]
                success, encoded = cv2.imencode(".png", frame)
                if not success:
                    raise ValueError("failed to encode websocket frame")
                snapshot = message_payload.setdefault("snapshot", {})
                snapshot["image_format"] = "png_base64"
                snapshot["image"] = base64.b64encode(encoded.tobytes()).decode("ascii")
            message = json.dumps(message_payload, ensure_ascii=True)
        except Exception:
            logging.exception("failed to build websocket payload")
            return
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
