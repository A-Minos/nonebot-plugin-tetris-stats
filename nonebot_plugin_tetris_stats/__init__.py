from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require_plugins = {
    'nonebot_plugin_alconna',
    'nonebot_plugin_apscheduler',
    'nonebot_plugin_localstore',
    'nonebot_plugin_orm',
    'nonebot_plugin_session_orm',
    'nonebot_plugin_session',
    'nonebot_plugin_user',
    'nonebot_plugin_userinfo',
    'nonebot_plugin_waiter',
}

for i in require_plugins:
    require(i)

from nonebot_plugin_alconna import namespace  # noqa: E402

with namespace('tetris_stats') as ns:
    ns.enable_message_cache = False

from .config import migrations  # noqa: E402
from .config.config import Config  # noqa: E402

__plugin_meta__ = PluginMetadata(
    name='Tetris Stats',
    description='一个用于查询 Tetris 相关游戏玩家数据的插件',
    usage='发送 tstats --help 查询使用方法',
    type='application',
    homepage='https://github.com/A-minos/nonebot-plugin-tetris-stats',
    config=Config,
    supported_adapters=inherit_supported_adapters(*require_plugins),
    extra={
        'orm_version_location': migrations,
    },
)

from . import games  # noqa: F401, E402
