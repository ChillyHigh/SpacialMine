from typing import Any

from config import Config
from executor.base import AbstractHandler
from executor.gui import GuiOperator, load_recipe
from executor.types import BackgroundTask, Result


class SmeltHandler(AbstractHandler):
    """Start a smelting task only when furnace GUI is already open."""

    action_type = "smelt"
    is_async = False

    def __init__(self, config: Config | None = None) -> None:
        """Create a smelt handler with shared executor configuration."""

        super().__init__()
        self.config = config or Config()

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Start smelting only after the furnace GUI has been opened."""

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
        try:
            recipe = load_recipe(self.config, str(params["item"]))
        except OSError as exc:
            return Result(False, self.action_type, "failed", task_id, None, str(exc), None)
        if recipe.get("type") != "minecraft:smelting":
            return Result(False, self.action_type, "failed", task_id, None, f"{params['item']} is not a smelting recipe", None)
        operator = GuiOperator(env, self.step, self.cancel, self.config)
        try:
            steps = operator.smelt(str(params["item"]), int(params["count"]), recipe, str(params.get("fuel", "coals")))
        except InterruptedError:
            return Result(False, self.action_type, "cancelled", task_id, operator.steps, None, None)
        except AssertionError as exc:
            return Result(False, self.action_type, "failed", task_id, operator.steps, str(exc), None)
        return Result(True, self.action_type, "done", task_id, steps, None, task)


class TakeFurnaceOutputHandler(AbstractHandler):
    """Take completed smelting output from an already open furnace GUI."""

    action_type = "take_furnace_output"
    is_async = False

    def __init__(self, config: Config | None = None) -> None:
        """Create a furnace-output handler with shared executor configuration."""

        super().__init__()
        self.config = config or Config()

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Move furnace result items into the player inventory."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if getattr(env, "gui_state", "none") != "furnace":
            return Result(
                success=False,
                action_type=self.action_type,
                status="failed",
                task_id=None,
                steps_taken=None,
                failure_reason="take_furnace_output requires furnace gui to be open first",
                smelt_task=None,
            )
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)
        operator = GuiOperator(env, self.step, self.cancel, self.config)
        try:
            steps = operator.take_furnace_output(int(params["count"]))
        except InterruptedError:
            return Result(False, self.action_type, "cancelled", None, operator.steps, None, None)
        except AssertionError as exc:
            return Result(False, self.action_type, "failed", None, operator.steps, str(exc), None)
        return Result(True, self.action_type, "done", None, steps, None, None)
