from arclet.alconna import Arg
from nonebot_plugin_alconna import Args, At, Subcommand

from ....utils.typedefs import Me
from .. import command as base_command
from .. import get_player

command = Subcommand(
    'record',
    Args(
        Arg(
            'who',
            At | Me | get_player,
            notice='@想要查询的人 / 自己 / TETR.IO 用户名 / ID',
        ),
    ),
)

from . import blitz, sprint  # noqa: E402

base_command.add(command)

__all__ = [
    'blitz',
    'sprint',
]
