from asyncio import sleep
from collections.abc import Awaitable, Callable
from datetime import timedelta
from functools import wraps
from typing import TypeVar, cast

from nonebot.log import logger

T = TypeVar('T')


def retry(
    max_attempts: int = 3,
    exception_type: type[BaseException] | tuple[type[BaseException], ...] = Exception,
    delay: timedelta | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:  # noqa: ANN002, ANN003
            attempts = 0
            while attempts < max_attempts + 1:
                try:
                    return await func(*args, **kwargs)
                except exception_type as e:  # noqa: PERF203
                    logger.exception(e)
                    attempts += 1
                    if attempts <= max_attempts:
                        if delay is not None:
                            await sleep(delay.total_seconds())
                        logger.debug(f'Retrying: {func.__name__} ({attempts}/{max_attempts})')
                        continue
                    raise
            raise RuntimeError('Unexpectedly reached the end of the retry loop')

        return cast(Callable[..., Awaitable[T]], wrapper)

    return decorator
