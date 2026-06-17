def main() -> None:
    """Run a manual tool-level demo from smelting iron to crafting an iron pickaxe."""

    input("Start Minecraft demo: smelt iron ingots, then craft an iron pickaxe. Press Enter...")

    from agent.tools import AgentTools
    from config import Config
    from executor import Executor
    from executor.debug_callbacks import DebugSetupCallback

    debug_inventory = [
        {"slot": 1, "type": "iron_ore", "quantity": 3},
        {"slot": 2, "type": "coal", "quantity": 4},
        {"slot": 3, "type": "stick", "quantity": 2},
        {"slot": 4, "type": "oak_planks", "quantity": 8},
    ]
    debug_commands = [
        "/tp @s -1838 72 30501 0 0",
        "/setblock ^ ^ ^3 minecraft:furnace",
        "/setblock ^1 ^ ^3 minecraft:crafting_table",
    ]
    config = Config(
        env_seed=1,
        env_callbacks=(DebugSetupCallback(debug_commands, debug_inventory),),
    )
    executor = Executor(config)
    tools = AgentTools(executor, config)
    try:
        print(executor.check())
        print("Debug inventory loaded:", debug_inventory)
        print("Debug commands loaded:", debug_commands)

        print(tools.open_furnace())
        print(tools.smelt("iron_ingot", 3, "coals"))
        print("Background tasks after smelt:", executor.payload()["background_tasks"])
        input("Wait until three iron ingots are ready in the furnace, then press Enter...")

        print(tools.open_furnace())
        print(tools.take_furnace_output())
        print("Background tasks after taking output:", executor.payload()["background_tasks"])

        print(tools.open_crafting_table())
        print(tools.craft("iron_pickaxe", 1))
        print(executor.check())
    finally:
        executor.shutdown()


if __name__ == "__main__":
    main()
