import json
import math
import random
import re
from pathlib import Path
from threading import Event
from typing import Any, Callable

import numpy as np

from config import Config

StepFn = Callable[[dict[str, Any]], tuple[Any, dict[str, Any]]]

BASE_WIDTH = 640
BASE_HEIGHT = 360
CAMERA_SCALER = 360.0 / 2400.0

KEY_POS_INVENTORY = {
    "resource_slot": {"left-top": (329, 114), "right-bottom": (365, 150), "row": 2, "col": 2, "prefix": "resource", "start_id": 0},
    "result_slot": {"left-top": (385, 124), "right-bottom": (403, 142), "row": 1, "col": 1, "prefix": "result", "start_id": 0},
    "hotbar_slot": {"left-top": (239, 238), "right-bottom": (401, 256), "row": 1, "col": 9, "prefix": "inventory", "start_id": 0},
    "inventory_slot": {"left-top": (239, 180), "right-bottom": (401, 234), "row": 3, "col": 9, "prefix": "inventory", "start_id": 9},
}
KEY_POS_TABLE = {
    "resource_slot": {"left-top": (261, 113), "right-bottom": (315, 167), "row": 3, "col": 3, "prefix": "resource", "start_id": 0},
    "result_slot": {"left-top": (351, 127), "right-bottom": (377, 153), "row": 1, "col": 1, "prefix": "result", "start_id": 0},
    "hotbar_slot": {"left-top": (239, 238), "right-bottom": (401, 256), "row": 1, "col": 9, "prefix": "inventory", "start_id": 0},
    "inventory_slot": {"left-top": (239, 180), "right-bottom": (401, 234), "row": 3, "col": 9, "prefix": "inventory", "start_id": 9},
}
KEY_POS_FURNACE = {
    "resource_slot": {"left-top": (287, 113), "right-bottom": (303, 164), "row": 2, "col": 1, "prefix": "resource", "start_id": 0},
    "result_slot": {"left-top": (345, 127), "right-bottom": (368, 152), "row": 1, "col": 1, "prefix": "result", "start_id": 0},
    "hotbar_slot": {"left-top": (242, 236), "right-bottom": (401, 256), "row": 1, "col": 9, "prefix": "inventory", "start_id": 0},
    "inventory_slot": {"left-top": (242, 178), "right-bottom": (401, 234), "row": 3, "col": 9, "prefix": "inventory", "start_id": 9},
}


def recipe_needs_table(recipe: dict[str, Any]) -> bool:
    """Return whether a Minecraft recipe needs a 3x3 crafting table."""

    if "pattern" in recipe:
        pattern = recipe["pattern"]
        return len(pattern) > 2 or len(pattern[0]) > 2
    return len(recipe["ingredients"]) > 4


class GuiOperator:
    """Operate Minecraft GUI slots through Executor-owned step calls."""

    def __init__(self, env: Any, step: StepFn, cancel: Event, config: Config) -> None:
        """Bind GUI mouse operations to the current MinecraftSim and executor step."""

        self.env = env
        self.step = step
        self.cancel = cancel
        self.config = config
        self.info = getattr(env, "info", {})
        self.steps = 0
        self.width, self.height = getattr(env, "render_size", (BASE_WIDTH, BASE_HEIGHT))
        self.cursor = [self.width // 2, self.height // 2]
        self.camera_scaler = CAMERA_SCALER / (self.width / BASE_WIDTH)
        self.resources = {f"resource_{index}": {"type": "none", "quantity": 0} for index in range(9)}
        self.inventory_slots = self.compute(KEY_POS_INVENTORY)
        self.table_slots = self.compute(KEY_POS_TABLE)
        self.furnace_slots = self.compute(KEY_POS_FURNACE)

    def compute(self, layout: dict[str, dict[str, Any]]) -> dict[str, tuple[float, float]]:
        """Scale GUI slot coordinates to the current render size."""

        width_ratio = self.width / BASE_WIDTH
        height_ratio = self.height / BASE_HEIGHT
        slots = {}
        for meta in layout.values():
            left = meta["left-top"][0] * width_ratio
            top = meta["left-top"][1] * height_ratio
            right = meta["right-bottom"][0] * width_ratio
            bottom = meta["right-bottom"][1] * height_ratio
            slot_width = (right - left) // meta["col"]
            slot_height = (bottom - top) // meta["row"]
            slot_id = 0
            for row in range(meta["row"]):
                for col in range(meta["col"]):
                    slots[f"{meta['prefix']}_{slot_id + meta['start_id']}"] = (
                        left + col * slot_width + slot_width // 2,
                        top + row * slot_height + slot_height // 2,
                    )
                    slot_id += 1
        return slots

    def press(self, name: str, wait: int = 5) -> None:
        """Press one MineStudio env action and optionally wait for GUI updates."""

        action = self.env.noop_action()
        action[name] = 1
        obs, info = self.step(action)
        self.info = info
        self.steps += 1
        for _ in range(wait):
            if self.cancel.is_set():
                raise InterruptedError
            obs, info = self.step(self.env.noop_action())
            self.info = info
            self.steps += 1

    def open_inventory(self) -> None:
        """Open the player inventory GUI."""

        self.press("inventory")
        self.cursor = [self.width // 2, self.height // 2]
        if not self.info.get("isGuiOpen", self.info.get("is_gui_open", False)):
            raise AssertionError("inventory gui did not open")
        self.env.gui_state = "inventory"

    def move_to(self, slots: dict[str, tuple[float, float]], slot: str) -> None:
        """Move the cursor to a named GUI slot."""

        if slot not in slots:
            raise AssertionError(f"unknown GUI slot: {slot}")
        target_x, target_y = slots[slot]
        camera_x = target_x - self.cursor[0]
        camera_y = target_y - self.cursor[1]
        distance = max(abs(camera_x), abs(camera_y))
        count = max(1, int(random.uniform(5, 10) * math.sqrt(distance) / 20))
        for _ in range(count):
            if self.cancel.is_set():
                raise InterruptedError
            action = self.env.noop_action()
            action["camera"] = np.array([(camera_y / count) * self.camera_scaler, (camera_x / count) * self.camera_scaler])
            obs, info = self.step(action)
            self.info = info
            self.cursor[0] += camera_x / count
            self.cursor[1] += camera_y / count
            self.steps += 1

    def click(self) -> None:
        """Left-click the current GUI slot."""

        self.press("attack", wait=1)

    def use(self) -> None:
        """Right-click the current GUI slot."""

        self.press("use", wait=1)

    def labels(self, resource_count: int) -> dict[str, Any]:
        """Return resource and inventory labels for recipe slot matching."""

        result = {}
        for index in range(resource_count):
            result[f"resource_{index}"] = self.resources[f"resource_{index}"]
        for slot, item in self.info["inventory"].items():
            result[f"inventory_{slot}"] = item
        return result

    def find_item(self, labels: dict[str, Any], item: str, item_type: str = "item") -> str | None:
        """Find the first inventory slot matching an item name or item tag."""

        if item_type == "tag":
            with open(Path(self.config.assets_dir) / "tag_items.json") as file:
                tag_info = json.load(file)
            for tag_item in tag_info.get(f"minecraft:{item}", []):
                found = self.find_item(labels, tag_item[10:], "item")
                if found is not None:
                    return found
            return None
        for key, value in labels.items():
            item_name = value.get("type") if isinstance(value, dict) else str(value)
            if item_name is not None and re.match(item, str(item_name)):
                return key
        return None

    def pull(self, slots: dict[str, tuple[float, float]], source: str, target: str, count: int) -> None:
        """Pick source, right-click target count times, and keep remaining stack selected."""

        if target.startswith("resource_"):
            self.resources[target] = self.info["inventory"][int(source.split("_")[-1])]
        self.move_to(slots, source)
        self.click()
        self.move_to(slots, target)
        for _ in range(count):
            self.use()

    def put_selected(self, slots: dict[str, tuple[float, float]], target: str) -> None:
        """Place the currently selected stack into a target slot."""

        self.move_to(slots, target)
        self.click()

    def take_result(self, slots: dict[str, tuple[float, float]], target: str, count: int) -> None:
        """Right-click result count times and place it into inventory."""

        self.move_to(slots, "result_0")
        for _ in range(count):
            self.use()
        self.put_selected(slots, target)

    def craft(self, target: str, count: int, recipe: dict[str, Any], gui: str) -> int:
        """Craft one recipe in an already open inventory or crafting table GUI."""

        slots = self.table_slots if gui == "crafting" else self.inventory_slots
        iter_count = math.ceil(count / int(recipe.get("result", {}).get("count", 1)))
        if "pattern" in recipe:
            labels = self.labels(9)
            grid_width = 3 if gui == "crafting" else 2
            for signal, ingredient in recipe["key"].items():
                item_type = "item" if "item" in ingredient else "tag"
                item = ingredient.get("item", ingredient.get("tag"))[10:]
                source = self.find_item(labels, item, item_type)
                if source is None:
                    raise AssertionError(f"not enough {item}")
                first = True
                for row, pattern_row in enumerate(recipe["pattern"]):
                    for col, cell in enumerate(pattern_row):
                        if cell == signal:
                            slot = f"resource_{row * grid_width + col}"
                            if first:
                                self.pull(slots, source, slot, iter_count)
                                first = False
                            else:
                                self.move_to(slots, slot)
                                for _ in range(iter_count):
                                    self.use()
                self.put_selected(slots, source)
        else:
            resource = 0
            for ingredient in recipe["ingredients"]:
                item_type = "item" if "item" in ingredient else "tag"
                item = ingredient.get("item", ingredient.get("tag"))[10:]
                labels = self.labels(9)
                source = self.find_item(labels, item, item_type)
                if source is None:
                    raise AssertionError(f"not enough {item}")
                self.pull(slots, source, f"resource_{resource}", iter_count)
                self.put_selected(slots, source)
                resource += 1
        labels = self.labels(9)
        for index in range(9):
            labels.pop(f"resource_{index}", None)
        target_slot = self.find_item(labels, target) or self.find_item(labels, "none")
        if target_slot is None:
            raise AssertionError("no space to place result")
        self.take_result(slots, target_slot, iter_count)
        return self.steps

    def smelt(self, target: str, count: int, recipe: dict[str, Any], fuel: str) -> int:
        """Place furnace ingredient and fuel in an already open furnace GUI."""

        ingredient = recipe["ingredient"]
        item_type = "item" if "item" in ingredient else "tag"
        item = ingredient.get("item", ingredient.get("tag"))[10:]
        labels = self.labels(2)
        source = self.find_item(labels, item, item_type)
        if source is None:
            raise AssertionError(f"not enough {item}")
        self.pull(self.furnace_slots, source, "resource_0", count)
        self.put_selected(self.furnace_slots, source)
        labels = self.labels(2)
        fuel_slot = self.find_item(labels, fuel, "tag")
        if fuel_slot is None:
            raise AssertionError("not enough fuels")
        self.pull(self.furnace_slots, fuel_slot, "resource_1", 1)
        self.put_selected(self.furnace_slots, fuel_slot)
        return self.steps

    def take_furnace_output(self, count: int) -> int:
        """Take smelted output from the furnace result slot into inventory."""

        labels = self.labels(2)
        target_slot = self.find_item(labels, "none")
        if target_slot is None:
            raise AssertionError("no space to place furnace output")
        self.take_result(self.furnace_slots, target_slot, count)
        return self.steps


def load_recipe(config: Config, item: str) -> dict[str, Any]:
    """Load one Minecraft recipe from the configured MineStudio assets."""

    with open(Path(config.assets_dir) / "recipes" / f"{item}.json") as file:
        return json.load(file)
