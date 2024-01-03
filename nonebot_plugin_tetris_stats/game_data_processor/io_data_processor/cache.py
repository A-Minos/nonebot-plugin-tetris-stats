from datetime import datetime, timezone

from aiocache import Cache as ACache  # type: ignore[import-untyped]
from nonebot.log import logger
from pydantic import parse_raw_as

from ...utils.request import Request
from .schemas.base import FailedModel, SuccessModel

UTC = timezone.utc


class Cache:
    cache = ACache(ACache.MEMORY)

    @classmethod
    async def get(cls, url: str) -> bytes:
        cached_data = await cls.cache.get(url)
        if cached_data is None:
            response_data = await Request.request(url)
            parsed_data: SuccessModel | FailedModel = parse_raw_as(SuccessModel | FailedModel, response_data)  # type: ignore[arg-type]
            if isinstance(parsed_data, SuccessModel):
                await cls.cache.add(
                    url,
                    response_data,
                    (parsed_data.cache.cached_until - datetime.now(UTC)).total_seconds(),
                )
            return response_data
        logger.debug(f'{url}: Cache hit!')
        return cached_data
