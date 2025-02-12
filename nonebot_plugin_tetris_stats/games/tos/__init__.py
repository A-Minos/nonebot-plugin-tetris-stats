from arclet.alconna import Arg, ArgFlag
from nonebot_plugin_alconna import Args, At, Subcommand

from ...utils.exception import MessageFormatError
from ...utils.typedefs import Me
from .. import add_block_handlers, alc, command
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


command.add(
    Subcommand(
        'TOS',
        Subcommand(
            'bind',
            Args(
                Arg(
                    'account',
                    get_player,
                    notice='茶服 用户名 / ID',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            help_text='绑定 茶服 账号',
        ),
        Subcommand(
            'unbind',
            help_text='解除绑定 TOS 账号',
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
                    notice='茶服 用户名 / TeaID',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
            ),
            help_text='查询 茶服 游戏信息',
        ),
        help_text='茶服 游戏相关指令',
    )
)

alc.shortcut(
    '(?i:tos|茶服)(?i:绑定|绑|bind)',
    command='tstats TOS bind',
    humanized='茶服绑定',
)
alc.shortcut(
    '(?i:tos|茶服)(?i:解除绑定|解绑|unbind)',
    command='tstats TOS unbind',
    humanized='茶服解绑',
)
alc.shortcut(
    '(?i:tos|茶服)(?i:查询|查|query|stats)',
    command='tstats TOS query',
    humanized='茶服查',
)

add_block_handlers(alc.assign('TOS.query'))

from . import bind, query, unbind  # noqa: E402, F401
