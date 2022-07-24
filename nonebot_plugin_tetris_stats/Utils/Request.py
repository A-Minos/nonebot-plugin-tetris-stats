from nonebot.log import logger

from typing import Any

import aiohttp


async def request(Url: str) -> tuple[bool, bool, dict[str, Any]]:
    # 封装请求函数
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(Url) as resp:
                data = await resp.json()
                return (True, data['success'], data)
    except aiohttp.client_exceptions.ClientConnectorError as e:
        logger.error(f'[TETRIS STATS] request.request: 请求错误\n{e}')
        return (False, False, {})
