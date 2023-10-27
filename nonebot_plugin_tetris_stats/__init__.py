from nonebot import require
from nonebot.plugin import PluginMetadata

require('nonebot_plugin_localstore')
require('nonebot_plugin_orm')
require('nonebot_plugin_alconna')

from .config.config import migrations  # noqa: E402

__plugin_meta__ = PluginMetadata(
    name='Tetris Stats',
    description='一个用于查询 Tetris 相关游戏玩家数据的插件',
    usage='发送 {游戏名}查 | query | stats{用户名/ID} 查询数据\n发送 {游戏名}绑定 | bind{用户名/ID} 绑定账号',
    type='application',
    homepage='https://github.com/shoucandanghehe/nonebot-plugin-tetris-stats',
    supported_adapters={'~onebot.v11', '~qq'},
    extra={
        'orm_version_location': migrations,
    },
)

from . import game_data_processor  # noqa: F401, E402
