from typing import Any

from executor.base import AbstractHandler
from executor.types import Result


class CraftHandler(AbstractHandler):
    """Craft action guarded by the executor's crafting GUI state."""

    action_type = "craft"
    is_async = False

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Run a low-level craft placeholder after crafting GUI is open."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)
        if env.gui_state != "crafting":
            return Result(
                success=False,
                action_type=self.action_type,
                status="failed",
                task_id=None,
                steps_taken=None,
                failure_reason="craft requires crafting gui to be open first",
                smelt_task=None,
            )
        count = int(params["count"])
        steps = 0
        while steps < count:
            if self.cancel.is_set():
                return Result(False, self.action_type, "cancelled", None, steps, None, None)
            self.step(env.noop_action())
            steps += 1
        return Result(True, self.action_type, "done", None, steps, None, None)
