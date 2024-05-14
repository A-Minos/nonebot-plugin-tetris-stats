from arclet.alconna import Alconna, AllParam, Arg, ArgFlag, Args, CommandMeta, Option
from nonebot_plugin_alconna import At, on_alconna

from ...utils.exception import MessageFormatError
from ...utils.typing import Me
from .. import add_default_handlers
from ..constant import BIND_COMMAND, QUERY_COMMAND
from .api import Player
from .constant import USER_NAME


def get_player(teaid_or_name: str) -> Player | MessageFormatError:
    if (
        teaid_or_name.startswith(('onebot-', 'qqguild-', 'kook-', 'discord-'))
        and teaid_or_name.split('-', maxsplit=1)[1].isdigit()
    ):
        return Player(teaid=teaid_or_name, trust=True)
    if USER_NAME.match(teaid_or_name) and not teaid_or_name.isdigit() and 2 <= len(teaid_or_name) <= 18:  # noqa: PLR2004
        return Player(user_name=teaid_or_name, trust=True)
    return MessageFormatError('用户名/ID不合法')


alc = on_alconna(
    Alconna(
        '茶服',
        Option(
            BIND_COMMAND[0],
            Args(
                Arg(
                    'account',
                    get_player,
                    notice='茶服 用户名 / TeaID',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            alias=BIND_COMMAND[1:],
            compact=True,
            dest='bind',
            help_text='绑定 茶服 账号',
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
                    notice='茶服 用户名 / TeaID',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
                # 如果放在一个 Union Args 里, 验证顺序不能保证, 可能出错
            ),
            alias=QUERY_COMMAND[1:],
            compact=True,
            dest='query',
            help_text='查询 茶服 游戏信息',
        ),
        Arg('other', AllParam, flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL]),
        meta=CommandMeta(
            description='查询 TetrisOnline茶服 的信息',
            example='茶服查我',
            compact=True,
            fuzzy_match=True,
        ),
    ),
    skip_for_unmatch=False,
    auto_send_output=True,
    aliases={'tos', 'TOS'},
)


from . import bind, query  # noqa: E402, F401

add_default_handlers(alc)
