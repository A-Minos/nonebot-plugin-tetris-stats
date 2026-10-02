from arclet.alconna import Arg, ArgFlag
from nonebot_plugin_alconna import Args, At, Option, Subcommand

from ...i18n import Lang
from ...utils.duration import parse_duration
from ...utils.exception import MessageFormatError
from ...utils.typedefs import Me
from .. import add_block_handlers, alc, assign, command
from .api import Player
from .constant import USER_NAME


def get_player(name: str) -> Player:
    if USER_NAME.match(name):
        return Player(user_name=name, trust=True)
    raise MessageFormatError(Lang.error.MessageFormatError.TOP)


command.add(
    Subcommand(
        'TOP',
        Subcommand(
            'bind',
            Args(
                Arg(
                    'account',
                    get_player,
                    notice=Lang.command.top.bind.args.account.notice.cast(),
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            help_text=Lang.command.top.bind.description.cast(),
        ),
        Subcommand(
            'unbind',
            help_text=Lang.command.top.unbind.description.cast(),
        ),
        Subcommand(
            'config',
            Option(
                '--default-compare',
                Arg(
                    'compare',
                    parse_duration,
                    notice=Lang.command.top.config.options.default_compare.args.compare.notice.cast(),
                ),
                alias=['-DC', 'DefaultCompare'],
                help_text=Lang.command.top.config.options.default_compare.help.cast(),
            ),
            help_text=Lang.command.top.config.description.cast(),
        ),
        Subcommand(
            'query',
            Args(
                Arg(
                    'who',
                    At | Me | get_player,
                    notice=Lang.command.top.query.args.who.notice.cast(),
                ),
            ),
            Option(
                '--compare',
                Arg(
                    'compare', parse_duration, notice=Lang.command.top.query.options.compare.args.compare.notice.cast()
                ),
                alias=['-C'],
                help_text=Lang.command.top.query.options.compare.help.cast(),
            ),
            help_text=Lang.command.top.query.description.cast(),
        ),
        help_text=Lang.command.top.description.cast(),
    )
)

alc.shortcut(
    '(?i:top)(?i:绑定|绑|bind)',
    command='tstats TOP bind',
    humanized=Lang.command.top.bind.shortcut.cast(),
)
alc.shortcut(
    '(?i:top)(?i:解除绑定|解绑|unbind)',
    command='tstats TOP unbind',
    humanized=Lang.command.top.unbind.shortcut.cast(),
)
alc.shortcut(
    '(?i:top)(?i:查询|查|query|stats)',
    command='tstats TOP query',
    humanized=Lang.command.top.query.shortcut.cast(),
)
alc.shortcut(
    '(?i:top)(?i:配置|配|config)',
    command='tstats TOP config',
    humanized=Lang.command.top.config.shortcut.cast(),
)

add_block_handlers(assign('TOP.query'))

from . import bind, config, query, unbind  # noqa: E402, F401
