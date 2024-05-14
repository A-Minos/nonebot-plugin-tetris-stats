from arclet.alconna import Alconna, AllParam, Arg, ArgFlag, Args, CommandMeta, Option
from nonebot_plugin_alconna import At, on_alconna

from ...utils.exception import MessageFormatError
from ...utils.typing import Me
from .. import add_default_handlers
from ..constant import BIND_COMMAND, QUERY_COMMAND
from .api import Player
from .api.typing import Rank
from .constant import USER_ID, USER_NAME


def get_player(user_id_or_name: str) -> Player | MessageFormatError:
    if USER_ID.match(user_id_or_name):
        return Player(user_id=user_id_or_name, trust=True)
    if USER_NAME.match(user_id_or_name):
        return Player(user_name=user_id_or_name, trust=True)
    return MessageFormatError('用户名/ID不合法')


alc = on_alconna(
    Alconna(
        'io',
        Option(
            BIND_COMMAND[0],
            Args(
                Arg(
                    'account',
                    get_player,
                    notice='IO 用户名 / ID',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            alias=BIND_COMMAND[1:],
            compact=True,
            dest='bind',
            help_text='绑定 IO 账号',
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
                    notice='IO 用户名 / ID',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
            ),
            alias=QUERY_COMMAND[1:],
            compact=True,
            dest='query',
            help_text='查询 IO 游戏信息',
        ),
        Option(
            'rank',
            Args(Arg('rank', Rank, notice='IO 段位')),
            alias={'Rank', 'RANK', '段位'},
            compact=True,
            dest='rank',
            help_text='查询 IO 段位信息',
        ),
        Arg('other', AllParam, flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL]),
        meta=CommandMeta(
            description='查询 TETR.IO 的信息',
            example='io绑定scdhh\nio查我\niorankx',
            compact=True,
            fuzzy_match=True,
        ),
    ),
    skip_for_unmatch=False,
    auto_send_output=True,
    aliases={'IO'},
)

alc.shortcut('fkosk', {'command': 'io查', 'args': ['我'], 'fuzzy': False, 'humanized': 'An Easter egg!'})

from . import bind, query, rank  # noqa: F401, E402

add_default_handlers(alc)
