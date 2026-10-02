from arclet.alconna import Arg, ArgFlag
from nonebot_plugin_alconna import Args, At, Option, Subcommand

from ...i18n import Lang
from ...utils.duration import parse_duration
from ...utils.exception import MessageFormatError
from ...utils.typedefs import Me
from .. import add_block_handlers, alc, assign, command
from .api import Player
from .constant import USER_NAME


def get_player(teaid_or_name: str) -> Player:
    if (
        teaid_or_name.startswith(('onebot-', 'qqguild-', 'kook-', 'discord-'))
        and teaid_or_name.split('-', maxsplit=1)[1].isdigit()
    ):
        return Player(teaid=teaid_or_name, trust=True)
    if USER_NAME.match(teaid_or_name) and not teaid_or_name.isdigit() and 2 <= len(teaid_or_name) <= 18:  # noqa: PLR2004
        return Player(user_name=teaid_or_name, trust=True)
    raise MessageFormatError(Lang.error.MessageFormatError.TOS)


command.add(
    Subcommand(
        'TOS',
        Subcommand(
            'bind',
            Args(
                Arg(
                    'account',
                    get_player,
                    notice=Lang.command.tos.bind.args.account.notice.cast(),
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            help_text=Lang.command.tos.bind.description.cast(),
        ),
        Subcommand(
            'unbind',
            help_text=Lang.command.tos.unbind.description.cast(),
        ),
        Subcommand(
            'config',
            Option(
                '--default-compare',
                Arg(
                    'compare',
                    parse_duration,
                    notice=Lang.command.tos.config.options.default_compare.args.compare.notice.cast(),
                ),
                alias=['-DC', 'DefaultCompare'],
                help_text=Lang.command.tos.config.options.default_compare.help.cast(),
            ),
            help_text=Lang.command.tos.config.description.cast(),
        ),
        Subcommand(
            'query',
            Args(
                Arg(
                    'who',
                    At | Me | get_player,
                    notice=Lang.command.tos.query.args.who.notice.cast(),
                ),
            ),
            Option(
                '--compare',
                Arg(
                    'compare', parse_duration, notice=Lang.command.tos.query.options.compare.args.compare.notice.cast()
                ),
                alias=['-C'],
                help_text=Lang.command.tos.query.options.compare.help.cast(),
            ),
            help_text=Lang.command.tos.query.description.cast(),
        ),
        help_text=Lang.command.tos.description.cast(),
    )
)

alc.shortcut(
    '(?i:tos|茶服)(?i:绑定|绑|bind)',
    command='tstats TOS bind',
    humanized=Lang.command.tos.bind.shortcut.cast(),
)
alc.shortcut(
    '(?i:tos|茶服)(?i:解除绑定|解绑|unbind)',
    command='tstats TOS unbind',
    humanized=Lang.command.tos.unbind.shortcut.cast(),
)
alc.shortcut(
    '(?i:tos|茶服)(?i:查询|查|query|stats)',
    command='tstats TOS query',
    humanized=Lang.command.tos.query.shortcut.cast(),
)
alc.shortcut(
    '(?i:tos|茶服)(?i:配置|配|config)',
    command='tstats TOS config',
    humanized=Lang.command.tos.config.shortcut.cast(),
)

add_block_handlers(assign('TOS.query'))

from . import bind, config, query, unbind  # noqa: E402, F401
