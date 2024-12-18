from nonebot_plugin_alconna import Subcommand

from ...utils.exception import MessageFormatError
from .. import alc
from .. import command as main_command
from .api import Player
from .constant import USER_ID, USER_NAME


def get_player(user_id_or_name: str) -> Player | MessageFormatError:
    if USER_ID.match(user_id_or_name):
        return Player(user_id=user_id_or_name, trust=True)
    if USER_NAME.match(user_id_or_name):
        return Player(user_name=user_id_or_name, trust=True)
    return MessageFormatError('用户名/ID不合法')


command = Subcommand(
    'TETR.IO',
    alias=['TETRIO', 'tetr.io', 'tetrio', 'io'],
    dest='TETRIO',
    help_text='TETR.IO 游戏相关指令',
)


from . import bind, config, list, query, rank, record, unbind  # noqa: A004, E402

main_command.add(command)

__all__ = [
    'alc',
    'bind',
    'config',
    'list',
    'query',
    'rank',
    'record',
    'unbind',
]
