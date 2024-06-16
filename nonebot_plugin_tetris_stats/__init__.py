from nonebot import require
from nonebot.plugin import PluginMetadata

require('nonebot_plugin_alconna')
require('nonebot_plugin_apscheduler')
require('nonebot_plugin_localstore')
require('nonebot_plugin_orm')
require('nonebot_plugin_session_orm')
require('nonebot_plugin_session')
require('nonebot_plugin_user')
require('nonebot_plugin_userinfo')

from nonebot_plugin_alconna import namespace  # noqa: E402

with namespace('tetris_stats') as ns:
    ns.enable_message_cache = False

from .config import migrations  # noqa: E402

__plugin_meta__ = PluginMetadata(
    name='Tetris Stats',
    description='一个用于查询 Tetris 相关游戏玩家数据的插件',
    usage='发送 tstats --help 查询使用方法',
    type='application',
    homepage='https://github.com/A-minos/nonebot-plugin-tetris-stats',
    extra={
        'orm_version_location': migrations,
    },
)

from . import games  # noqa: F401, E402
