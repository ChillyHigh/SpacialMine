from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Executor runtime configuration shared by main and tools."""

    env_obs_size: tuple[int, int] = (128, 128)
    env_seed: int = 0
    env_preferred_biome: str | None = None
    ws_host: str = "0.0.0.0"
    ws_port: int = 8765
