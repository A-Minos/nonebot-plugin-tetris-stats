from arclet.alconna import Arg, ArgFlag, Args, Option, Subcommand
from nonebot_plugin_alconna import At

from ...utils.exception import MessageFormatError
from ...utils.typing import Me
from .. import add_block_handlers, alc
from .api import Player
from .api.typing import ValidRank
from .constant import USER_ID, USER_NAME
from .typing import Template


def get_player(user_id_or_name: str) -> Player | MessageFormatError:
    if USER_ID.match(user_id_or_name):
        return Player(user_id=user_id_or_name, trust=True)
    if USER_NAME.match(user_id_or_name):
        return Player(user_name=user_id_or_name, trust=True)
    return MessageFormatError('用户名/ID不合法')


alc.command.add(
    Subcommand(
        'TETR.IO',
        Subcommand(
            'bind',
            Args(
                Arg(
                    'account',
                    get_player,
                    notice='TETR.IO 用户名 / ID',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            help_text='绑定 TETR.IO 账号',
        ),
        Subcommand(
            'query',
            Args(
                Arg(
                    'target',
                    At | Me,
                    notice='@想要查询的人 / 自己',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
                Arg(
                    'account',
                    get_player,
                    notice='TETR.IO 用户名 / ID',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
            ),
            Option(
                '--template',
                Arg('template', Template),
                alias=['-T'],
                help_text='要使用的查询模板',
            ),
            help_text='查询 TETR.IO 游戏信息',
        ),
        Subcommand(
            'rank',
            Args(Arg('rank', ValidRank, notice='TETR.IO 段位')),
            help_text='查询 TETR.IO 段位信息',
        ),
        Subcommand(
            'config',
            Option(
                '--default-template',
                Arg('template', Template),
                alias=['-DT', 'DefaultTemplate'],
            ),
        ),
        dest='TETRIO',
        help_text='TETR.IO 游戏相关指令',
    )
)

alc.shortcut('(?i:io)(?i:绑定|绑|bind)', {'command': 'tstats TETR.IO bind', 'humanized': 'io绑定'})
alc.shortcut('(?i:io)(?i:查询|查|query|stats)', {'command': 'tstats TETR.IO query', 'humanized': 'io查'})
alc.shortcut('(?i:io)(?i:配置|配|config)', {'command': 'tstats TETR.IO config', 'humanized': 'io配置'})

alc.shortcut(
    'fkosk', {'command': 'tstats TETR.IO query', 'args': ['我'], 'fuzzy': False, 'humanized': 'An Easter egg!'}
)

add_block_handlers(alc.assign('TETRIO.query'))

from . import bind, config, query, rank  # noqa: F401, E402
