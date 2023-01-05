from functools import wraps
from time import time_ns
from typing import Any, Awaitable, Callable, Type

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
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


async def send(cls: Type, *args, **kwargs):
    game_type = getattr(cls, 'game_type', None)
    command_type = getattr(cls, 'command_type', None)
    user_id = getattr(cls, 'user_id', None)
    command_args = getattr(cls, 'command_args', None)
    response = getattr(cls, 'response', None)
    processed_data = getattr(cls, 'processed_data', None)
    logger.debug(
        f'game_type: {game_type}, command_type: {command_type}, user_id: {user_id}, command_args: {command_args}, response: {response}, processed_data: {processed_data}'
    )


def recorder(collector: AsyncCallable):
    def _inner(func: AsyncCallable):
        @wraps(func)
        async def _wrapper(*args, **kwargs):
            await collector(*args, **kwargs)
            ret = await func(*args, **kwargs)
            return ret

        return _wrapper

    return _inner
