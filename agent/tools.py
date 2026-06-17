from typing import Any

from langchain_core.tools import ToolException

from config import Config
from executor import Executor
from executor.craft import CraftHandler
from executor.dig import DigHandler
from executor.navigate import NavigateHandler
from executor.open_gui import OpenCraftingTableHandler, OpenFurnaceHandler
from executor.place import PlaceBlockHandler
from executor.smelt import SmeltHandler, TakeFurnaceOutputHandler
from executor.steve import SteveHandler
from executor.types import Result


class AgentTools:
    """LLM-facing tools that access Minecraft only through Executor."""

    def __init__(self, executor: Executor, config: Config) -> None:
        """Bind tool methods to one executor runtime and shared configuration."""

        self.executor = executor
        self.config = config

    def craft(self, item: str, count: int) -> str:
        """Craft an item using the current inventory or crafting table GUI."""

        result = self.executor.submit(CraftHandler(self.config), {"item": item, "count": count})
        if not result.success:
            raise ToolException(result.failure_reason or "craft failed")
        return f"craft {item} x{count} done"

    def smelt(self, item: str, count: int, fuel: str = "coals") -> str:
        """Place smelting inputs into an already open furnace GUI."""

        result = self.executor.submit(SmeltHandler(self.config), {"item": item, "count": count, "fuel": fuel})
        if not result.success:
            raise ToolException(result.failure_reason or "smelt failed")
        return f"smelt {item} x{count} started"

    def take_furnace_output(self, count: int) -> str:
        """Take completed smelting output from the open furnace GUI."""

        result = self.executor.submit(TakeFurnaceOutputHandler(self.config), {"count": count})
        if not result.success:
            raise ToolException(result.failure_reason or "take_furnace_output failed")
        return f"take furnace output x{count} done"

    def open_crafting_table(self) -> str:
        """Open the crafting table currently under the crosshair."""

        result = self.executor.submit(OpenCraftingTableHandler(self.config), {})
        if not result.success:
            raise ToolException(result.failure_reason or "open_crafting_table failed")
        return "crafting table gui opened"

    def open_furnace(self) -> str:
        """Open the furnace currently under the crosshair."""

        result = self.executor.submit(OpenFurnaceHandler(self.config), {})
        if not result.success:
            raise ToolException(result.failure_reason or "open_furnace failed")
        return "furnace gui opened"

    def place_block(self, block_type: str) -> str:
        """Place or use the currently selected block through Executor."""

        result = self.executor.submit(PlaceBlockHandler(self.config), {"block_type": block_type})
        if not result.success:
            raise ToolException(result.failure_reason or "place_block failed")
        return f"place {block_type} done"

    def dig_to_level(self, steps: int, forward: bool = False) -> str:
        """Start an async dig task for a bounded number of steps."""

        result = self.executor.submit(DigHandler(), {"steps": steps, "forward": forward})
        if not result.success:
            raise ToolException(result.failure_reason or "dig_to_level failed")
        return f"dig_to_level started: {result.task_id}"

    def navigate(self, direction: str, max_steps: int, sprint: bool = False, jump: bool = False) -> str:
        """Start an async movement task."""

        result = self.executor.submit(
            NavigateHandler(),
            {"direction": direction, "max_steps": max_steps, "sprint": sprint, "jump": jump},
        )
        if not result.success:
            raise ToolException(result.failure_reason or "navigate failed")
        return f"navigate started: {result.task_id}"

    def send_prompt(self, text: str, steps: int | None = None) -> str:
        """Reserve the executor for a STEVE prompt task placeholder."""

        params: dict[str, Any] = {"text": text}
        if steps is not None:
            params["steps"] = steps
        result = self.executor.submit(SteveHandler(self.config), params)
        if not result.success:
            raise ToolException(result.failure_reason or "send_prompt failed")
        return f"send_prompt started: {result.task_id}"

    def check_executor(self) -> str:
        """Return executor status as a compact string."""

        return str(self.executor.check())

    def cancel_task(self) -> str:
        """Cancel the current async executor task."""

        result: Result = self.executor.cancel_task()
        if not result.success and result.status != "cancelled":
            raise ToolException(result.failure_reason or "cancel_task failed")
        return f"cancelled task: {result.task_id}"
