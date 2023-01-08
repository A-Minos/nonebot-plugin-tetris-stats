from functools import wraps
from time import time_ns
from typing import Any, Awaitable, Callable, Type

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import FinishedException
from nonebot.log import logger

AsyncCallable = Callable[..., Awaitable[Any]]


async def receive(bot: Bot, event: MessageEvent, *args, **kwargs):
    message_id = event.message_id
    message_time = time_ns()
    bot_id = bot.self_id
    source_id = event.get_session_id()
    message = event.raw_message
    logger.debug(
        f'message_id: {message_id}, time: {message_time}, bot_id: {bot_id}, source_id: {source_id}, message: {message}'
    )


async def send(cls: Type, ret: Any, *args, **kwargs):
    game_type = getattr(cls, 'GAME_TYPE', None)
    user = getattr(cls, 'user', None)
    command_type = getattr(cls, 'command_type', None)
    command_args = getattr(cls, 'command_args', None)
    response = getattr(cls, 'response', None)
    processed_data = getattr(cls, 'processed_data', None)
    logger.debug(
        f'game_type: {game_type}, command_type: {command_type}, user: {user}, command_args: {command_args}, response: {response}, processed_data: {processed_data}, return_message: {ret}'
    )


def recorder(collector: AsyncCallable):
    def _inner(func: AsyncCallable):
        @wraps(func)
        async def _wrapper(*args, **kwargs):
            try:
                ret = await func(*args, **kwargs)
            except FinishedException:
                ret = None
            await collector(ret=ret, *args, **kwargs)
            # 或许应该把 try 放到 receive函数里
            return ret

        return _wrapper

    return _inner
