from typing import Any

from minestudio.simulator.callbacks.callback import MinecraftCallback


class DebugSetupCallback(MinecraftCallback):
    """Initialize a debug world after MineStudio reset using Minecraft commands."""

    def __init__(self, commands: list[str], inventory: list[dict[str, Any]]) -> None:
        """Store commands and inventory slots to apply after reset."""

        super().__init__()
        self.commands = commands
        self.inventory = inventory

    def after_reset(self, sim: Any, obs: Any, info: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        """Teleport, place blocks, fill inventory, and wait for state updates."""

        obs, reward, done, info = sim.env.execute_cmd("/gamerule sendCommandFeedback false")
        for command in self.commands:
            obs, reward, done, info = sim.env.execute_cmd(command)
        for item in self.inventory:
            slot_number = int(item["slot"])
            if slot_number == 0:
                slot = "weapon.mainhand"
            elif slot_number == 40:
                slot = "weapon.offhand"
            elif 36 <= slot_number <= 39:
                slot = {36: "armor.feet", 37: "armor.legs", 38: "armor.chest", 39: "armor.head"}[slot_number]
            elif 1 <= slot_number <= 8:
                slot = f"hotbar.{slot_number}"
            elif 9 <= slot_number <= 35:
                slot = f"inventory.{slot_number - 9}"
            else:
                raise ValueError(f"invalid inventory slot: {slot_number}")
            command = f"/replaceitem entity @p {slot} minecraft:{item['type']} {int(item['quantity'])}"
            obs, reward, done, info = sim.env.execute_cmd(command)
        for _ in range(30):
            obs, reward, done, info = sim.env.step(sim.env.noop_action())
        missing = []
        inventory = obs.get("inventory", {})
        equipped = obs.get("equipped_items", {})
        for item in self.inventory:
            slot = int(item["slot"])
            current = inventory.get(slot, inventory.get(str(slot), {}))
            if slot == 0 and current.get("type") in {None, "none"}:
                mainhand = equipped.get("mainhand", {})
                if isinstance(mainhand, str):
                    current = {"type": mainhand, "quantity": item["quantity"]}
                else:
                    current = mainhand
            if current.get("type") != item["type"] or int(current.get("quantity", 0)) < int(item["quantity"]):
                missing.append(item)
        if missing:
            raise AssertionError(f"debug inventory setup failed: {missing}")
        return sim._wrap_obs_info(obs, info)
