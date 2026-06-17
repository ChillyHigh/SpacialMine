from typing import Any

from executor.base import AbstractHandler
from executor.types import Result


class SteveHandler(AbstractHandler):
    """Asynchronous STEVE prompt placeholder owned by Executor."""

    action_type = "steve"
    is_async = True

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Run one low-level step for the current STEVE prompt request."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)
        self.step(env.noop_action())
        return Result(True, self.action_type, "done", None, 1, None, None)
