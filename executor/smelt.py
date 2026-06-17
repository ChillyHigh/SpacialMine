from typing import Any

from executor.base import AbstractHandler
from executor.types import BackgroundTask, Result


class SmeltHandler(AbstractHandler):
    """Start a smelting task only when furnace GUI is already open."""

    action_type = "smelt"
    is_async = False

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Place smelt work into background tracking without waiting."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if getattr(env, "gui_state", "none") != "furnace":
            return Result(
                success=False,
                action_type=self.action_type,
                status="failed",
                task_id=None,
                steps_taken=None,
                failure_reason="smelt requires furnace gui to be open first",
                smelt_task=None,
            )
        task_id = params.get("task_id") or "smelt-" + params["item"]
        task = BackgroundTask(
            task_id=task_id,
            action_type=self.action_type,
            status="running",
            item=params["item"],
            count=int(params["count"]),
        )
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)
        self.step(env.noop_action())
        return Result(True, self.action_type, "done", task_id, 1, None, task)
