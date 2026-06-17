from typing import Any

from config import Config
from executor.base import AbstractHandler
from executor.types import GuiState, Result


class PlaceBlockHandler(AbstractHandler):
    """Place-block handler using the low-level simulator action space."""

    action_type = "place_block"
    is_async = False

    def __init__(self, config: Config | None = None) -> None:
        """Create a place handler with shared executor configuration."""

        super().__init__()
        self.config = config or Config()

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Place or use the selected hotbar block with a right-click action."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)
        action = env.noop_action()
        action["use"] = 1
        self.step(action)
        steps = 1
        for _ in range(self.config.place_wait_steps):
            if self.cancel.is_set():
                return Result(False, self.action_type, "cancelled", None, steps, None, None)
            self.step(env.noop_action())
            steps += 1
        env.gui_state = GuiState("none")
        return Result(True, self.action_type, "done", None, steps, None, None)
