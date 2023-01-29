from functools import wraps
from time import time
from typing import Any, Type

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.log import logger

# from ..db.database import DataBase
from .typing import AsyncCallable


class Recorder:
    @classmethod
    async def receive(
        cls, func: AsyncCallable, bot: Bot, event: MessageEvent, *args, **kwargs
    ) -> Any:
        message_id = event.message_id
        message_time = int(time())
        bot_id = bot.self_id
        source_id = event.get_session_id()
        message = event.raw_message
        logger.debug(
            f'''
    message_id: {message_id}
    time: {message_time}
    bot_id: {bot_id}
    source_id: {source_id}
    message: {message}
    '''
        )
        kwargs.update(bot=bot, event=event)
        ret = await func(*args, **kwargs)
        return ret

    @classmethod
    async def send(cls, func: AsyncCallable, instance: Type, *args, **kwargs) -> Any:
        args = (instance,)
        ret = await func(*args, **kwargs)
        message_id = getattr(instance, 'message_id', None)
        call_time = int(time())
        game_type = getattr(instance, 'GAME_TYPE', None)
        user = getattr(instance, 'user', None)
        command_type = getattr(instance, 'command_type', None)
        command_args = getattr(instance, 'command_args', None)
        response = getattr(instance, 'response', None)
        processed_data = getattr(instance, 'processed_data', None)
        logger.debug(
            f'''
    message_id: {message_id}
    call_time: {call_time}
    game_type: {game_type}
    command_type: {command_type}
    user: {user}
    command_args: {command_args}
    response: {response}
    processed_data: {processed_data}
    return_message: {ret}
    '''
        )
        return ret

    @classmethod
    def recorder(cls, collector: AsyncCallable):
        def _inner(func: AsyncCallable):
            @wraps(func)
            async def _wrapper(*args, **kwargs):
                ret = await collector(func, *args, **kwargs)
                return ret

            return _wrapper

        return _inner
