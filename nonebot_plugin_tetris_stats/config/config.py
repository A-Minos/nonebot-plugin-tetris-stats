from nonebot_plugin_localstore import get_cache_dir, get_data_dir
from pydantic import BaseModel, Field

CACHE_PATH = get_cache_dir('nonebot_plugin_tetris_stats')
DATA_PATH = get_data_dir('nonebot_plugin_tetris_stats')


class ScopedConfig(BaseModel):
    request_timeout: float = 30.0
    screenshot_quality: float = 2


class Config(BaseModel):
    tetris: ScopedConfig = Field(default_factory=ScopedConfig)
