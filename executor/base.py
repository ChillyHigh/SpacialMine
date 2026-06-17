from abc import ABC, abstractmethod
from threading import Event
from typing import TYPE_CHECKING, Any, Callable, ClassVar

if TYPE_CHECKING:
    from minestudio.simulator import MinecraftSim
else:
    MinecraftSim = Any

from executor.types import Result

StepFn = Callable[[dict[str, Any]], tuple[Any, dict[str, Any]]]
SnapshotFn = Callable[[Any, dict[str, Any]], None]


class AbstractHandler(ABC):
    """Executor handler contract."""

    action_type: ClassVar[str]
    is_async: ClassVar[bool]

    def __init__(self) -> None:
        """Create an unbound handler; Executor binds callbacks at submit time."""

        self.step: StepFn | None = None
        self.publish: SnapshotFn | None = None
        self.cancel: Event | None = None

    def bind(self, step: StepFn, publish: SnapshotFn, cancel: Event) -> None:
        """Attach Executor-owned callbacks before run is called."""

        self.step = step
        self.publish = publish
        self.cancel = cancel

    @abstractmethod
    def run(self, env: MinecraftSim, params: dict[str, Any]) -> Result:
        """Run the action and return one executor Result."""
