from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    """Executor runtime configuration shared by main and tools."""

    env_obs_size: tuple[int, int] = (128, 128)
    env_seed: int = 0
    env_preferred_biome: str | None = None
    ws_host: str = "0.0.0.0"
    ws_port: int = 8765
    assets_dir: str = str(ROOT_DIR / "assets")
    gui_wait_steps: int = 5
    place_wait_steps: int = 2
    steve_steps: int = 20
