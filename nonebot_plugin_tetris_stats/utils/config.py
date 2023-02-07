from pathlib import Path

from nonebot import require
from pydantic import BaseModel

require('nonebot_plugin_datastore')

from nonebot_plugin_datastore import get_plugin_data  # type: ignore # noqa: E402

plugin_data = get_plugin_data()

CACHE_PATH: Path = plugin_data.cache_dir


class Config(BaseModel):
    """配置类"""

    db_url: str = 'sqlite://data/nonebot_plugin_tetris_stats/data.db'
