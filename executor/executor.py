import os
import threading
import uuid
from typing import Any

from minestudio.simulator import MinecraftSim

from config import Config
from executor.base import AbstractHandler
from executor.types import BackgroundTask, ExecutorStatus, GameSnapshot, Result
from executor.ws import SnapshotServer


class Executor:
    """Unique owner of MinecraftSim and all env mutations."""

    def __init__(self, config: Config) -> None:
        """Create MinecraftSim, reset it, and start the ws side channel."""

        os.environ.setdefault("MINESTUDIO_DIR", "/mnt/home/user42/ChillyHigh/minestudio_data")
        self.config = config
        self.env = MinecraftSim(
            action_type="env",
            obs_size=config.env_obs_size,
            seed=config.env_seed or 0,
            preferred_spawn_biome=config.env_preferred_biome,
        )
        self.lock = threading.Lock()
        self.cancel_event = threading.Event()
        self.latest_snapshot: GameSnapshot | None = None
        self.background_tasks: dict[str, BackgroundTask] = {}
        self.last_result: Result | None = None
        self.status = "idle"
        self.current_task: str | None = None
        self.task_id: str | None = None
        self.step_count = 0
        self.ws = SnapshotServer(config.ws_host, config.ws_port)
        self.ws.start()
        self.env.gui_state = "none"
        obs, info = self.env.reset()
        self.publish(obs, info)

    def submit(self, handler: AbstractHandler, params: dict[str, Any]) -> Result:
        """Run or start one handler; return busy failure instead of queuing."""

        handler.bind(self.step, self.publish, self.cancel_event)
        with self.lock:
            if self.status == "running":
                return Result(
                    success=False,
                    action_type=handler.action_type,
                    status="failed",
                    task_id=None,
                    steps_taken=None,
                    failure_reason=(
                        f"executor is busy: current task {self.current_task} is running; "
                        "call check_executor or cancel_task first"
                    ),
                    smelt_task=None,
                )
            if handler.is_async:
                task_id = uuid.uuid4().hex
                self.status = "running"
                self.current_task = handler.action_type
                self.task_id = task_id
                self.cancel_event.clear()
                threading.Thread(
                    target=self.run_async,
                    args=(handler, params, task_id),
                    name=f"executor-{handler.action_type}",
                    daemon=True,
                ).start()
                result = Result(
                    success=True,
                    action_type=handler.action_type,
                    status="started",
                    task_id=task_id,
                    steps_taken=None,
                    failure_reason=None,
                    smelt_task=None,
                )
                self.last_result = result
                self.ws.publish(self.payload())
                return result
            self.status = "running"
            self.current_task = handler.action_type
            self.task_id = None
            self.cancel_event.clear()

        result = None
        try:
            result = handler.run(self.env, params)
            self.last_result = result
            if result.smelt_task is not None:
                self.background_tasks[result.smelt_task.task_id] = result.smelt_task
            self.status = result.status if result.status in {"done", "failed", "cancelled"} else "done"
            return result
        finally:
            with self.lock:
                if result is None and self.status == "running":
                    self.status = "failed"
                self.current_task = None
                self.task_id = None
                self.ws.publish(self.payload())

    def run_async(self, handler: AbstractHandler, params: dict[str, Any], task_id: str) -> None:
        """Run an async handler in the worker thread and store its final result."""

        try:
            result = handler.run(self.env, params)
            self.last_result = Result(
                success=result.success,
                action_type=result.action_type,
                status=result.status,
                task_id=task_id,
                steps_taken=result.steps_taken,
                failure_reason=result.failure_reason,
                smelt_task=result.smelt_task,
            )
            if result.smelt_task is not None:
                self.background_tasks[result.smelt_task.task_id] = result.smelt_task
            self.status = result.status
        finally:
            with self.lock:
                self.current_task = None
                self.task_id = None
                if self.status == "running":
                    self.status = "failed"
                self.ws.publish(self.payload())

    def step(self, action: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        """Advance MinecraftSim once and publish the resulting snapshot."""

        obs, reward, terminated, truncated, info = self.env.step(action)
        self.step_count += 1
        self.publish(obs, info)
        return obs, info

    def publish(self, obs: Any, info: dict[str, Any]) -> None:
        """Update latest_snapshot and emit it through the non-blocking ws server."""

        if info.get("isGuiOpen") is False:
            self.env.gui_state = "none"
        pov = obs.get("image") if isinstance(obs, dict) and "image" in obs else None
        if pov is None and isinstance(obs, dict):
            pov = obs.get("pov")
        self.latest_snapshot = GameSnapshot(
            obs=obs,
            info=info,
            pov=pov,
            step_count=self.step_count,
            gui=self.env.gui_state,
        )
        self.ws.publish(self.payload())

    def check(self) -> ExecutorStatus:
        """Return the current executor status without touching MinecraftSim."""

        return ExecutorStatus(
            status=self.status,
            current_task=self.current_task,
            task_id=self.task_id,
            last_result=self.last_result,
            gui=self.env.gui_state,
        )

    def cancel_task(self) -> Result:
        """Request cooperative cancellation for the current async task."""

        with self.lock:
            if self.status != "running" or self.task_id is None:
                return Result(
                    success=False,
                    action_type="cancel_task",
                    status="failed",
                    task_id=None,
                    steps_taken=None,
                    failure_reason="executor has no running async task",
                    smelt_task=None,
                )
            self.cancel_event.set()
            return Result(
                success=False,
                action_type="cancel_task",
                status="cancelled",
                task_id=self.task_id,
                steps_taken=None,
                failure_reason=None,
                smelt_task=None,
            )

    def shutdown(self) -> None:
        """Stop the ws side channel and close MinecraftSim."""

        self.cancel_event.set()
        self.ws.stop()
        self.env.close()

    def payload(self) -> dict[str, Any]:
        """Build the ws payload from current executor state."""

        return {
            "status": self.check(),
            "snapshot": self.latest_snapshot,
            "background_tasks": list(self.background_tasks.values()),
        }
