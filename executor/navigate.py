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
        direction = str(params["direction"])
        if direction not in {"forward", "back", "left", "right"}:
            return Result(
                success=False,
                action_type=self.action_type,
                status="failed",
                task_id=None,
                steps_taken=None,
                failure_reason=f"unsupported navigate direction: {direction}",
                smelt_task=None,
            )
        steps = 0
        while steps < int(params["max_steps"]):
            if self.cancel.is_set():
                return Result(False, self.action_type, "cancelled", None, steps, None, None)
            action = env.noop_action()
            action[direction] = 1
            if bool(params.get("sprint", False)) and direction == "forward":
                action["sprint"] = 1
            if bool(params.get("jump", False)):
                action["jump"] = 1
            self.step(action)
            steps += 1
        env.gui_state = "none"
        return Result(True, self.action_type, "done", None, steps, None, None)
