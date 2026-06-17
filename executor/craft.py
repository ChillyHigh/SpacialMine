from typing import Any

from config import Config
from executor.base import AbstractHandler
from executor.gui import GuiOperator, load_recipe, recipe_needs_table
from executor.types import Result


class CraftHandler(AbstractHandler):
    """Craft action guarded by the executor's crafting GUI state."""

    action_type = "craft"
    is_async = False

    def __init__(self, config: Config | None = None) -> None:
        """Create a craft handler with shared executor configuration."""

        super().__init__()
        self.config = config or Config()

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Craft in the currently open inventory or crafting table GUI."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)
        try:
            recipe = load_recipe(self.config, str(params["item"]))
        except OSError as exc:
            return Result(False, self.action_type, "failed", None, None, str(exc), None)
        needs_table = recipe_needs_table(recipe)
        if env.gui_state == "none":
            if needs_table:
                return Result(
                    success=False,
                    action_type=self.action_type,
                    status="failed",
                    task_id=None,
                    steps_taken=None,
                    failure_reason="craft requires crafting gui to be open first",
                    smelt_task=None,
                )
            operator = GuiOperator(env, self.step, self.cancel, self.config)
            try:
                operator.open_inventory()
            except AssertionError as exc:
                return Result(False, self.action_type, "failed", None, operator.steps, str(exc), None)
        if env.gui_state not in {"inventory", "crafting"}:
            return Result(
                success=False,
                action_type=self.action_type,
                status="failed",
                task_id=None,
                steps_taken=None,
                failure_reason=f"craft cannot run while {env.gui_state} gui is open",
                smelt_task=None,
            )
        if needs_table and env.gui_state != "crafting":
            return Result(False, self.action_type, "failed", None, None, "crafting table recipe requires crafting gui", None)
        operator = GuiOperator(env, self.step, self.cancel, self.config)
        try:
            steps = operator.craft(str(params["item"]), int(params["count"]), recipe, env.gui_state)
        except InterruptedError:
            return Result(False, self.action_type, "cancelled", None, operator.steps, None, None)
        except AssertionError as exc:
            return Result(False, self.action_type, "failed", None, operator.steps, str(exc), None)
        return Result(True, self.action_type, "done", None, steps, None, None)
