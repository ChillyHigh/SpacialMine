import math
from typing import Any, ClassVar

import numpy as np

from config import Config
from executor.base import AbstractHandler
from executor.types import BlockPos, GuiState, Result


class OpenGuiHandler(AbstractHandler):
    """Turn toward the nearest target block, right-click it, and record GUI state."""

    is_async = False
    action_type: ClassVar[str]
    block_type: ClassVar[str]
    gui_state: ClassVar[str]
    gui_name: ClassVar[str]

    def __init__(self, config: Config | None = None) -> None:
        """Create an open-gui handler with shared configuration."""

        super().__init__()
        self.config = config or Config()

    def run(self, env: Any, params: dict[str, Any]) -> Result:
        """Open the nearest matching work-block GUI without moving the player."""

        if self.step is None or self.publish is None or self.cancel is None:
            raise RuntimeError("handler is not bound")
        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, None, None, None)

        target = None
        target_pos = None
        best_distance = None
        obs, info = self.step(env.noop_action())
        steps = 1
        voxels = info.get("voxels")
        if not isinstance(voxels, list):
            return Result(False, self.action_type, "failed", None, steps, "open_gui did not receive voxels from MinecraftSim", None)
        player = info.get("player_pos", {})
        if not {"x", "y", "z"} <= set(player):
            return Result(False, self.action_type, "failed", None, steps, "player position is missing from info", None)
        for voxel in voxels:
            if not isinstance(voxel, dict):
                continue
            block_type = str(voxel.get("type", "")).removeprefix("minecraft:")
            if block_type != self.block_type:
                continue
            dx = float(voxel["x"]) + 0.5
            dy = float(voxel["y"]) + 0.5 - 1.62
            dz = float(voxel["z"]) + 0.5
            distance = dx * dx + dy * dy + dz * dz
            if best_distance is None or distance < best_distance:
                best_distance = distance
                target = (dx, dy, dz)
                target_pos = BlockPos(
                    math.floor(float(player["x"]) + float(voxel["x"])),
                    math.floor(float(player["y"]) + float(voxel["y"])),
                    math.floor(float(player["z"]) + float(voxel["z"])),
                )

        if target is None:
            return Result(False, self.action_type, "failed", None, steps, f"no nearby {self.block_type} in voxels", None)

        dx, dy, dz = target
        target_yaw = math.degrees(math.atan2(dz, dx)) - 90.0
        target_pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
        target_pitch = max(-90.0, min(90.0, target_pitch))
        for _ in range(self.config.open_gui_turn_steps):
            if self.cancel.is_set():
                return Result(False, self.action_type, "cancelled", None, steps, None, None)
            player = info.get("player_pos", {})
            if not {"yaw", "pitch"} <= set(player):
                return Result(False, self.action_type, "failed", None, steps, "player rotation is missing from info", None)
            delta_yaw = (target_yaw - float(player["yaw"]) + 180.0) % 360.0 - 180.0
            delta_pitch = target_pitch - float(player["pitch"])
            if abs(delta_yaw) <= 1.0 and abs(delta_pitch) <= 1.0:
                break
            step_yaw = max(-self.config.open_gui_camera_step, min(self.config.open_gui_camera_step, delta_yaw))
            step_pitch = max(-self.config.open_gui_camera_step, min(self.config.open_gui_camera_step, delta_pitch))
            action = env.noop_action()
            action["camera"] = np.array([step_pitch, step_yaw], dtype=np.float32)
            obs, info = self.step(action)
            steps += 1

        if self.cancel.is_set():
            return Result(False, self.action_type, "cancelled", None, steps, None, None)
        action = env.noop_action()
        action["use"] = 1
        obs, info = self.step(action)
        steps += 1

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
                f"{self.gui_name} gui did not open after turning toward nearest {self.block_type}",
                None,
            )
        env.gui_state = GuiState(self.gui_state, target_pos)
        self.publish(obs, info)
        return Result(True, self.action_type, "done", None, steps, None, None)


class OpenCraftingTableHandler(OpenGuiHandler):
    """Turn toward and open the nearest crafting table GUI."""

    action_type = "open_crafting_table"
    block_type = "crafting_table"
    gui_state = "crafting"
    gui_name = "crafting table"


class OpenFurnaceHandler(OpenGuiHandler):
    """Turn toward and open the nearest furnace GUI."""

    action_type = "open_furnace"
    block_type = "furnace"
    gui_state = "furnace"
    gui_name = "furnace"
