from nonebot import require

require('nonebot_plugin_localstore')
require('nonebot_plugin_orm')

from . import game_data_processor  # noqa: F401, E402
