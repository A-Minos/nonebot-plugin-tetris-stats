from nonebot import get_plugin_config
from nonebot_plugin_localstore import get_cache_dir, get_data_dir
from pydantic import BaseModel, Field

CACHE_PATH = get_cache_dir('nonebot_plugin_tetris_stats')
DATA_PATH = get_data_dir('nonebot_plugin_tetris_stats')


class Proxy(BaseModel):
    main: str | None = None
    github: str | None = None
    tetrio: str | None = None
    tos: str | None = None
    top: str | None = None


class ScopedConfig(BaseModel):
    request_timeout: float = 30.0
    screenshot_quality: float = 2
    proxy: Proxy = Field(default_factory=Proxy)


class Config(BaseModel):
    tetris: ScopedConfig = Field(default_factory=ScopedConfig)


config = get_plugin_config(Config)
