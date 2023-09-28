from asyncio import get_running_loop
from datetime import datetime
from functools import wraps
from typing import Any, Type

from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.log import logger
from tortoise.timezone import now

from ..db.database import DataBase
from .typing import AsyncCallable, CommandType, GameType


class Recorder:
    class Temp:
        receive_time: datetime | None = None
        bot_id: str | None = None
        source_type: str | None = None
        source_id: str | None = None
        message_id: int | None = None
        message: str | None = None
        call_time: datetime | None = None
        game_type: GameType | None = None
        command_type: CommandType | None = None
        command_args: str | None = None
        user: dict | None = None
        response: dict | None = None
        processed_data: dict | None = None
        return_message: bytes | None = None
        send_time: datetime | None = None
        saved: bool = False

        def save(self):
            get_running_loop().create_task(DataBase.write_historical(**self.__dict__))
            self.saved = True

        def __del__(self):
            if self.saved is False:
                logger.warning('在保存之前就调用了 del, 如果处理过程中发生了异常, 这可能是正确的')
                self.save()

    instances: dict[str, Temp] = {}

    @classmethod
    async def receive(
        cls, func: AsyncCallable, bot: Bot, event: MessageEvent, *args, **kwargs
    ) -> Any:
        receive_time = now()  # 保证时间最接近 (?
        message_id = event.message_id
        temp = cls._create_temp_instance(cls._message_id_to_id(message_id))
        temp.receive_time = receive_time
        temp.bot_id = bot.self_id
        temp.source_type = event.get_event_name()
        temp.source_id = event.get_session_id()
        temp.message_id = message_id
        temp.message = event.raw_message
        kwargs.update(bot=bot, event=event)
        ret = await func(*args, **kwargs)
        return ret

    @classmethod
    async def send(cls, func: AsyncCallable, instance: Type, *args, **kwargs) -> Any:
        call_time = now()
        message_id = getattr(instance, 'message_id', None)
        temp = cls._get_temp_instance(cls._message_id_to_id(message_id))
        temp.call_time = call_time
        temp.game_type = getattr(instance, 'GAME_TYPE', None)
        args = (instance,)
        ret = await func(*args, **kwargs)
        temp.send_time = now()
        temp.command_type = getattr(instance, 'command_type', None)
        temp.command_args = getattr(instance, 'command_args', None)
        temp.user = getattr(instance, 'user', None)
        temp.response = getattr(instance, 'response', None)
        temp.processed_data = getattr(instance, 'processed_data', None)
        temp.return_message = bytes(ret, 'UTF-8') if isinstance(ret, str) else ret
        cls._save_temp_instance(cls._message_id_to_id(message_id))
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

    @classmethod
    def _message_id_to_id(cls, message_id) -> str:
        return str(message_id)

    @classmethod
    def _create_temp_instance(cls, id: str) -> Temp:
        if id in cls.instances:
            logger.warning('可能出现了撞 message_id 或者其他神秘问题')
            del cls.instances[id]
        cls.instances[id] = cls.Temp()
        return cls._get_temp_instance(id)

    @classmethod
    def _get_temp_instance(cls, id: str) -> Temp:
        return cls.instances[id]

    @classmethod
    def _save_temp_instance(cls, id: str) -> None:
        cls._get_temp_instance(id).save()
        cls.__del_temp(id)

    @classmethod
    def __del_temp(cls, id: str) -> None:
        del cls.instances[id]
