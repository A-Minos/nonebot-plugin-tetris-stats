from pathlib import Path

from nonebot import get_driver, get_plugin_config
from nonebot_plugin_localstore import get_plugin_cache_dir, get_plugin_data_dir
from pydantic import BaseModel, Field

CACHE_PATH = get_plugin_cache_dir()
DATA_PATH = get_plugin_data_dir()


class Proxy(BaseModel):
    main: str | None = None
    github: str | None = None
    tetrio: str | None = None
    tos: str | None = None
    top: str | None = None


class Dev(BaseModel):
    enabled: bool = False
    template_path: Path | None = None
    enable_template_check: bool = True


class ScopedConfig(BaseModel):
    request_timeout: float = 30.0
    screenshot_quality: float = 2
    proxy: Proxy = Field(default_factory=Proxy)
    dev: Dev = Field(default_factory=Dev)


class Config(BaseModel):
    tetris: ScopedConfig = Field(default_factory=ScopedConfig)


config = get_plugin_config(Config)
global_config = get_driver().config
