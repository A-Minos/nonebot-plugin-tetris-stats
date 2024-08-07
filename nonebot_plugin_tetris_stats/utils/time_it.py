from collections.abc import Callable, Coroutine
from functools import wraps
from time import time_ns
from typing import Any, ParamSpec, TypeVar

from nonebot.log import logger

T = TypeVar('T')
P = ParamSpec('P')


def time_it(func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, Coroutine[Any, Any, T]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start = time_ns()
        try:
            return await func(*args, **kwargs)
        finally:
            logger.debug(f'{func.__name__} took {(time_ns() - start) / 1e6}ms')

    return wrapper
