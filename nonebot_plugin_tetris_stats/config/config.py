from pathlib import Path

from nonebot_plugin_localstore import get_cache_dir  # type: ignore[import-untyped]
from pydantic import BaseModel

CACHE_PATH: Path = get_cache_dir('nonebot_plugin_tetris_stats')


class Config(BaseModel):
    """配置类"""

    tetris_req_timeout: float = 30.0
