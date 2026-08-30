from nonebot.internal.params import DependsInner
from nonebot_plugin_permission import depends_permission  # type: ignore[import-untyped]


def permission_name(game: str, command: str) -> str:
    return f'tetris.{game.upper()}.{command.lower()}'


def command_permission(game: str, command: str) -> tuple[DependsInner]:
    return (depends_permission(permission_name(game, command), default_available=True),)
