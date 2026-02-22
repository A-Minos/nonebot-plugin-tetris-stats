from arclet.alconna import Arg, ArgFlag
from nonebot_plugin_alconna import Args, At, Option, Subcommand

from ...utils.duration import parse_duration
from ...utils.exception import MessageFormatError
from ...utils.typedefs import Me
from .. import add_block_handlers, alc, command
from .api import Player
from .constant import USER_NAME


def get_player(name: str) -> Player | MessageFormatError:
    if USER_NAME.match(name):
        return Player(user_name=name, trust=True)
    return MessageFormatError('用户名/ID不合法')


command.add(
    Subcommand(
        'TOP',
        Subcommand(
            'bind',
            Args(
                Arg(
                    'account',
                    get_player,
                    notice='TOP 用户名 / ID',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            help_text='绑定 TOP 账号',
        ),
        Subcommand(
            'unbind',
            help_text='解除绑定 TOP 账号',
        ),
        Subcommand(
            'config',
            Option(
                '--default-compare',
                Arg('compare', parse_duration, notice='对比时间距离'),
                alias=['-DC', 'DefaultCompare'],
                help_text='设置默认对比时间距离',
            ),
            help_text='TOP 查询个性化配置',
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
                    notice='TOP 用户名',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
            ),
            Option(
                '--compare',
                Arg('compare', parse_duration),
                alias=['-C'],
                help_text='指定对比时间距离',
            ),
            help_text='查询 TOP 游戏信息',
        ),
        help_text='TOP 游戏相关指令',
    )
)

alc.shortcut(
    '(?i:top)(?i:绑定|绑|bind)',
    command='tstats TOP bind',
    humanized='top绑定',
)
alc.shortcut(
    '(?i:top)(?i:解除绑定|解绑|unbind)',
    command='tstats TOP unbind',
    humanized='top解绑',
)
alc.shortcut(
    '(?i:top)(?i:查询|查|query|stats)',
    command='tstats TOP query',
    humanized='top查',
)
alc.shortcut(
    '(?i:top)(?i:配置|配|config)',
    command='tstats TOP config',
    humanized='top配置',
)

add_block_handlers(alc.assign('TOP.query'))

from . import bind, config, query, unbind  # noqa: E402, F401
