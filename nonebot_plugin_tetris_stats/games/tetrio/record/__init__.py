from arclet.alconna import Arg, ArgFlag
from nonebot_plugin_alconna import Args, At, Subcommand

from ....utils.typedefs import Me
from .. import command as base_command
from .. import get_player

command = Subcommand(
    'record',
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
)

from . import blitz, sprint  # noqa: E402

base_command.add(command)

__all__ = [
    'blitz',
    'sprint',
]
