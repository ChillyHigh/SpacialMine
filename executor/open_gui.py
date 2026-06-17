from typing import Any

from executor.base import AbstractHandler
from executor.types import Result


class OpenCraftingTableHandler(AbstractHandler):
    """Open and record crafting table GUI state."""

    action_type = "open_crafting_table"
    is_async = False

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Mark crafting GUI open after one low-level environment step."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)
        obs, info = self.step(env.noop_action())
        env.gui_state = "crafting"
        self.publish(obs, info)
        return Result(True, self.action_type, "done", None, 1, None, None)


class OpenFurnaceHandler(AbstractHandler):
    """Open and record furnace GUI state."""

    action_type = "open_furnace"
    is_async = False

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Mark furnace GUI open after one low-level environment step."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)
        obs, info = self.step(env.noop_action())
        env.gui_state = "furnace"
        self.publish(obs, info)
        return Result(True, self.action_type, "done", None, 1, None, None)
