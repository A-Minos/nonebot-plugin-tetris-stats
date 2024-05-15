from asyncio import Lock
from datetime import datetime, timezone
from typing import ClassVar
from weakref import WeakValueDictionary

from aiocache import Cache as ACache  # type: ignore[import-untyped]
from nonebot.compat import type_validate_json
from nonebot.log import logger

from ....utils.request import Request
from .schemas.base import FailedModel, SuccessModel

UTC = timezone.utc


class Cache:
    cache = ACache(ACache.MEMORY)
    task: ClassVar[WeakValueDictionary[str, Lock]] = WeakValueDictionary()

    @classmethod
    async def get(cls, url: str) -> bytes:
        lock = cls.task.setdefault(url, Lock())
        async with lock:
            if (cached_data := await cls.cache.get(url)) is not None:
                logger.debug(f'{url}: Cache hit!')
                return cached_data
            response_data = await Request.request(url)
            parsed_data: SuccessModel | FailedModel = type_validate_json(SuccessModel | FailedModel, response_data)  # type: ignore[arg-type]
            if isinstance(parsed_data, SuccessModel):
                await cls.cache.add(
                    url,
                    response_data,
                    (parsed_data.cache.cached_until - datetime.now(UTC)).total_seconds(),
                )
            return response_data
