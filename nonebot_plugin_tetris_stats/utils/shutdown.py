from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec

from nonebot import require
from nonebot.exception import FinishedException

from ..config.config import config

P = ParamSpec('P')


def graceful_query(handler: Callable[P, Coroutine[Any, Any, None]]) -> Callable[P, Coroutine[Any, Any, None]]:
    if not config.tetris.graceful_shutdown:
        return handler

    require('nonebot_plugin_wait_a_minute')
    from nonebot_plugin_wait_a_minute import graceful  # noqa: PLC0415

    @graceful(block=True)
    async def tracked(*args: P.args, **kwargs: P.kwargs) -> FinishedException | None:
        try:
            await handler(*args, **kwargs)
        except FinishedException as finished:
            return finished
        return None

    @wraps(handler)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> None:
        if (finished := await tracked(*args, **kwargs)) is not None:
            raise finished

    wrapped.__setattr__('__graceful_hook__', True)
    return wrapped
