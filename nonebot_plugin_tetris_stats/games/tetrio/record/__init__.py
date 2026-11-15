from arclet.alconna import Arg
from nonebot_plugin_alconna import Args, At, Option, Subcommand

from ....i18n import Lang
from ....utils.typedefs import Me
from .. import command as base_command
from .. import get_player
from ..api.player import RecordType

command = Subcommand(
    'record',
    Args(
        Arg(
            'who',
            At | Me | get_player,
            notice=Lang.command.tetrio.record.args.who.notice.cast(),
        ),
    ),
    Option(
        '--type',
        Arg(
            'record_type',
            {item.value: item for item in RecordType},
            notice=Lang.command.tetrio.record.options.type.args.record_type.notice.cast(),
        ),
        help_text=Lang.command.tetrio.record.options.type.help.cast(),
    ),
    Option(
        '--index',
        Arg('index', int, notice=Lang.command.tetrio.record.options.index.args.index.notice.cast()),
        help_text=Lang.command.tetrio.record.options.index.help.cast(),
    ),
    help_text=Lang.command.tetrio.record.description.cast(),
)


from . import blitz, sprint  # noqa: E402

base_command.add(command)

__all__ = [
    'blitz',
    'sprint',
]
