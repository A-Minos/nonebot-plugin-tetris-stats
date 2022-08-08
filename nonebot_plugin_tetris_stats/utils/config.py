from pydantic import BaseModel


class Config(BaseModel):
    cache_path: str = 'cache/nonebot_plugin_tetris_stats/cache'
