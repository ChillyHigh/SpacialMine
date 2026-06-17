from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class GameSnapshot:
    """Latest observation published by Executor after reset or step."""

    obs: Any
    info: dict[str, Any]
    pov: Any
    step_count: int
    gui: Literal["none", "inventory", "crafting", "furnace"]


@dataclass(frozen=True)
class BackgroundTask:
    """Longer game-side process tracked after a synchronous tool starts it."""

    task_id: str
    action_type: str
    status: Literal["running", "done", "failed", "cancelled"]
    item: str | None = None
    count: int | None = None
    failure_reason: str | None = None


@dataclass(frozen=True)
class Result:
    """Single result contract returned by every executor operation."""

    success: bool
    action_type: str
    status: Literal["started", "done", "failed", "cancelled"]
    task_id: str | None
    steps_taken: int | None
    failure_reason: str | None
    smelt_task: BackgroundTask | None


@dataclass(frozen=True)
class ExecutorStatus:
    """Current executor state visible to tools and the LLM."""

    status: Literal["idle", "running", "done", "failed", "cancelled"]
    current_task: str | None
    task_id: str | None
    last_result: Result | None
    gui: Literal["none", "inventory", "crafting", "furnace"]
