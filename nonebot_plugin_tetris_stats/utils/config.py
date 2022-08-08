from pydantic import BaseModel


class Config(BaseModel):
    cache_path: str = 'cache/nonebot_plugin_tetris_stats/cache'
    db_path: str = 'data/nonebot_plugin_tetris_stats/data.db'
