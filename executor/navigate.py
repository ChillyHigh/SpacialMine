from typing import Any

from executor.base import AbstractHandler
from executor.types import Result


class NavigateHandler(AbstractHandler):
    """Asynchronous movement loop controlled by executor cancellation."""

    action_type = "navigate"
    is_async = True

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Run navigation steps until max_steps is exhausted or cancelled."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        steps = 0
        while steps < int(params["max_steps"]):
            if self.cancel.is_set():
                return Result(False, self.action_type, "cancelled", None, steps, None, None)
            self.step(env.noop_action())
            steps += 1
        return Result(True, self.action_type, "done", None, steps, None, None)
