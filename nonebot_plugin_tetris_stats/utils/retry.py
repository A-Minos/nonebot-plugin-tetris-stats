from asyncio import sleep
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import timedelta
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from nonebot.log import logger
from nonebot_plugin_alconna.uniseg import SerializeFailed, UniMessage

T = TypeVar('T')
P = ParamSpec('P')


def retry(
    max_attempts: int = 3,
    exception_type: type[BaseException] | tuple[type[BaseException], ...] = Exception,
    delay: timedelta | None = None,
    reply: str | UniMessage | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            for i in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exception_type as e:  # noqa: PERF203
                    logger.exception(e)
                    if delay is not None:
                        await sleep(delay.total_seconds())
                    message = f'Retrying: {func.__name__} ({i}/{max_attempts})'
                    logger.debug(message)
                    with suppress(SerializeFailed):
                        await UniMessage(reply or message).send()
            msg = 'Unexpectedly reached the end of the retry loop'
            raise RuntimeError(msg)

        return cast(Callable[P, Awaitable[T]], wrapper)

    return decorator
