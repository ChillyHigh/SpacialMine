from typing import Any

from config import Config
from executor.base import AbstractHandler
from executor.types import Result


class SteveHandler(AbstractHandler):
    """Asynchronous STEVE prompt placeholder owned by Executor."""

    action_type = "steve"
    is_async = True

    def __init__(self, config: Config | None = None) -> None:
        """Create a STEVE handler with shared executor configuration."""

        super().__init__()
        self.config = config or Config()

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Reserve env ownership for a STEVE prompt until policy integration exists."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        steps = 0
        while steps < int(params.get("steps", self.config.steve_steps)):
            if self.cancel.is_set():
                return Result(False, self.action_type, "cancelled", None, steps, None, None)
            self.step(env.noop_action())
            steps += 1
        return Result(True, self.action_type, "done", None, steps, None, None)
