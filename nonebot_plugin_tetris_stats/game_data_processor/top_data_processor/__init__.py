from arclet.alconna import Alconna, AllParam, Arg, ArgFlag, Args, CommandMeta, Option
from nonebot_plugin_alconna import At, on_alconna

from ...utils.exception import MessageFormatError
from ...utils.typing import Me
from .. import add_default_handlers
from ..constant import BIND_COMMAND, QUERY_COMMAND
from .api import Player
from .constant import USER_NAME


def get_player(name: str) -> Player | MessageFormatError:
    if USER_NAME.match(name):
        return Player(user_name=name, trust=True)
    return MessageFormatError('用户名/ID不合法')


alc = on_alconna(
    Alconna(
        'top',
        Option(
            BIND_COMMAND[0],
            Args(
                Arg(
                    'account',
                    get_player,
                    notice='TOP 用户名',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            alias=BIND_COMMAND[1:],
            compact=True,
            dest='bind',
            help_text='绑定 TOP 账号',
        ),
        Option(
            QUERY_COMMAND[0],
            Args(
                Arg(
                    'target',
                    At | Me,
                    notice='@想要查询的人 | 自己',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
                Arg(
                    'account',
                    get_player,
                    notice='TOP 用户名',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
            ),
            alias=QUERY_COMMAND[1:],
            compact=True,
            dest='query',
            help_text='查询 TOP 游戏信息',
        ),
        Arg('other', AllParam, flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL]),
        meta=CommandMeta(
            description='查询 TetrisOnline波兰服 的信息',
            example='top绑定scdhh\ntop查我',
            compact=True,
            fuzzy_match=True,
        ),
    ),
    skip_for_unmatch=False,
    auto_send_output=True,
    aliases={'TOP'},
)

from . import bind, query  # noqa: E402, F401

add_default_handlers(alc)
