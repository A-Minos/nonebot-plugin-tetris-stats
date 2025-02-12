from asyncio import Lock, sleep
from collections.abc import Callable, Coroutine
from datetime import timedelta
from functools import wraps
from time import time
from typing import Any, ParamSpec, TypeVar

from nonebot.log import logger

P = ParamSpec('P')
T = TypeVar('T')


def limit(limit: timedelta) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    limit_seconds = limit.total_seconds()

    def decorator(func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, Coroutine[Any, Any, T]]:
        last_call = 0.0
        lock = Lock()

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            nonlocal last_call
            async with lock:
                if (diff := (time() - last_call)) < limit_seconds:
                    logger.debug(
                        f'func: {func.__name__} trigger limit, wait {(limit_time := limit_seconds - diff):.3f}s'
                    )
                    await sleep(limit_time)
            last_call = time()
            return await func(*args, **kwargs)

        return wrapper

    return decorator
