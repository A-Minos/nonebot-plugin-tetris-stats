from nonebot.internal.params import DependsInner
from nonebot.matcher import Matcher
from nonebot.params import Depends
from nonebot_plugin_permission import require_permission  # type: ignore[import-untyped]

from .i18n import Lang


def permission_name(game: str, command: str) -> str:
    return f'tetris.{game.upper()}.{command.lower()}'


def command_permission(game: str, command: str, *, default_available: bool = True) -> tuple[DependsInner]:
    check = require_permission(permission_name(game, command), default_available=default_available)

    async def check_permission(matcher: Matcher, *, allowed: bool = Depends(check)) -> None:
        if not allowed:
            await matcher.finish(Lang.interaction.permission_denied())

    return (Depends(check_permission),)
