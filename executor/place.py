from typing import Any

from executor.base import AbstractHandler
from executor.types import Result


class PlaceBlockHandler(AbstractHandler):
    """Place-block handler using the low-level simulator action space."""

    action_type = "place_block"
    is_async = False

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Perform one placement placeholder step and return synchronously."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)
        self.step(env.noop_action())
        return Result(True, self.action_type, "done", None, 1, None, None)
