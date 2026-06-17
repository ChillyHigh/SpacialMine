from typing import Any

from executor.base import AbstractHandler
from executor.types import Result


class DigHandler(AbstractHandler):
    """Asynchronous dig loop controlled by executor cancellation."""

    action_type = "dig"
    is_async = True

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Run step-by-step digging work until steps are exhausted or cancelled."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        steps = 0
        while steps < int(params["steps"]):
            if self.cancel.is_set():
                return Result(False, self.action_type, "cancelled", None, steps, None, None)
            action = env.noop_action()
            action["attack"] = 1
            if bool(params.get("forward", False)):
                action["forward"] = 1
            self.step(action)
            steps += 1
        env.gui_state = "none"
        return Result(True, self.action_type, "done", None, steps, None, None)
