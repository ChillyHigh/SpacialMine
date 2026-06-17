from typing import Any

from config import Config
from executor.base import AbstractHandler
from executor.types import Result


class OpenCraftingTableHandler(AbstractHandler):
    """Open and record crafting table GUI state."""

    action_type = "open_crafting_table"
    is_async = False

    def __init__(self, config: Config | None = None) -> None:
        """Create an open-crafting handler with shared configuration."""

        super().__init__()
        self.config = config or Config()

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Right-click the targeted crafting table and record GUI state."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)
        action = env.noop_action()
        action["use"] = 1
        obs, info = self.step(action)
        steps = 1
        for _ in range(self.config.gui_wait_steps):
            if self.cancel.is_set():
                return Result(False, self.action_type, "cancelled", None, steps, None, None)
            obs, info = self.step(env.noop_action())
            steps += 1
        if not info.get("isGuiOpen", info.get("is_gui_open", False)):
            return Result(
                False,
                self.action_type,
                "failed",
                None,
                steps,
                "crafting table gui did not open; face a crafting table before calling open_crafting_table",
                None,
            )
        env.gui_state = "crafting"
        self.publish(obs, info)
        return Result(True, self.action_type, "done", None, steps, None, None)


class OpenFurnaceHandler(AbstractHandler):
    """Open and record furnace GUI state."""

    action_type = "open_furnace"
    is_async = False

    def __init__(self, config: Config | None = None) -> None:
        """Create an open-furnace handler with shared configuration."""

        super().__init__()
        self.config = config or Config()

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Right-click the targeted furnace and record GUI state."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)
        action = env.noop_action()
        action["use"] = 1
        obs, info = self.step(action)
        steps = 1
        for _ in range(self.config.gui_wait_steps):
            if self.cancel.is_set():
                return Result(False, self.action_type, "cancelled", None, steps, None, None)
            obs, info = self.step(env.noop_action())
            steps += 1
        if not info.get("isGuiOpen", info.get("is_gui_open", False)):
            return Result(
                False,
                self.action_type,
                "failed",
                None,
                steps,
                "furnace gui did not open; face a furnace before calling open_furnace",
                None,
            )
        env.gui_state = "furnace"
        self.publish(obs, info)
        return Result(True, self.action_type, "done", None, steps, None, None)
