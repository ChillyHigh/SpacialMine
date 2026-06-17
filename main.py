def main() -> None:
    """Start MinecraftSim and run a small manual executor demo."""

    import time

    from config import Config
    from executor import Executor
    from executor.craft import CraftHandler
    from executor.dig import DigHandler
    from executor.open_gui import OpenCraftingTableHandler

    executor = Executor(Config())
    try:
        print(executor.check())
        print(executor.submit(CraftHandler(), {"item": "stick", "count": 1}))
        print(executor.submit(OpenCraftingTableHandler(), {}))
        print(executor.submit(CraftHandler(), {"item": "stick", "count": 1}))
        print(executor.submit(DigHandler(), {"steps": 3}))
        while executor.check().status == "running":
            time.sleep(0.1)
        print(executor.check())
    finally:
        executor.shutdown()


if __name__ == "__main__":
    main()
