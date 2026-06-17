def main() -> None:
    """Start MinecraftSim and run a small manual executor demo."""

    import time

    from config import Config
    from executor import Executor
    from executor.craft import CraftHandler
    from executor.debug_callbacks import DebugSetupCallback
    from executor.dig import DigHandler
    from executor.open_gui import OpenCraftingTableHandler

    debug_inventory = [
        {"slot": 0, "type": "planks", "quantity": 16},
        {"slot": 1, "type": "stick", "quantity": 8},
        {"slot": 2, "type": "iron_ore", "quantity": 4},
        {"slot": 3, "type": "coal", "quantity": 4},
        {"slot": 4, "type": "cobblestone", "quantity": 16},
    ]
    debug_commands = [
        "/tp @s -1838 72 30501 0 0",
        "/setblock ^ ^ ^3 minecraft:crafting_table",
        "/setblock ^1 ^ ^3 minecraft:furnace",
    ]
    executor = Executor(
        Config(
            env_seed=1,
            env_callbacks=(DebugSetupCallback(debug_commands, debug_inventory),),
        )
    )
    try:
        print(executor.check())
        print("Debug inventory loaded:", debug_inventory)
        print("Debug commands loaded:", debug_commands)
        print(executor.submit(CraftHandler(), {"item": "stick", "count": 1}))
        if executor.check().gui != "none":
            action = executor.env.noop_action()
            action["inventory"] = 1
            executor.step(action)
            for _ in range(5):
                executor.step(executor.env.noop_action())
            print(executor.check())
        input("A crafting table should be in front of you. Press Enter to test open_crafting_table...")
        print(executor.submit(OpenCraftingTableHandler(), {}))
        print(executor.submit(CraftHandler(), {"item": "wooden_pickaxe", "count": 1}))
        print(executor.submit(DigHandler(), {"steps": 3}))
        while executor.check().status == "running":
            time.sleep(0.1)
        print(executor.check())
    finally:
        executor.shutdown()


if __name__ == "__main__":
    main()
