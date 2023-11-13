from pathlib import Path

from nonebot_plugin_localstore import get_cache_dir  # type: ignore[import-untyped]
from pydantic import BaseModel

from . import migrations  # noqa: F401

CACHE_PATH: Path = get_cache_dir('nonebot_plugin_tetris_stats')


class Config(BaseModel):
    """配置类"""

    db_url: str = 'sqlite://data/nonebot_plugin_tetris_stats/data.db'
