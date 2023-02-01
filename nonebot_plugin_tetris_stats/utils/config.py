from pydantic import BaseModel


class Config(BaseModel):
    """配置类"""

    cache_path: str = 'cache/nonebot_plugin_tetris_stats/cache'
    db_url: str = 'sqlite://data/nonebot_plugin_tetris_stats/data.db'
