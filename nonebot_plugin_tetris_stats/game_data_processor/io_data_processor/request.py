from typing import Any

import aiohttp
from aiofiles import open
from nonebot import get_driver
from nonebot.log import logger
from playwright.async_api import Response
from ujson import JSONDecodeError, dumps, loads

from ...utils.browser import BrowserManager
from ...utils.config import CACHE_PATH

driver = get_driver()


@driver.on_startup
async def _():
    await Request.init_cache()
    await Request.read_cache()


@driver.on_shutdown
async def _():
    await Request.write_cache()


class Request:
    """网络请求相关类"""

    _CACHE_FILE = CACHE_PATH.joinpath('cloudflare_cache.json')
    _headers: dict | None = None
    _cookies: dict | None = None

    @classmethod
    async def _anti_cloudflare(cls, url: str) -> tuple[bool, bool, dict[str, Any]]:
        """用firefox硬穿五秒盾"""
        browser = await BrowserManager.get_browser()
        context = await browser.new_context()
        page = await context.new_page()
        response = await page.goto(url)
        attempts = 0
        while attempts < 60:  # noqa: PLR2004
            attempts += 1
            text = await page.locator('body').text_content()
            if text is None:
                await page.wait_for_timeout(1000)
                continue
            if await page.title() == 'Please Wait... | Cloudflare':
                logger.warning('疑似触发了 Cloudflare 的验证码')
                break
            try:
                data = loads(text)
            except JSONDecodeError:
                await page.wait_for_timeout(1000)
            else:
                assert isinstance(response, Response)
                cls._headers = await response.request.all_headers()
                try:
                    cls._cookies = {
                        i['name']: i['value'] for i in await context.cookies()
                    }
                except KeyError:
                    cls._cookies = None
                await page.close()
                await context.close()
                return True, data['success'], data
        await page.close()
        await context.close()
        return True, False, {'error': '绕过五秒盾失败'}

    @classmethod
    async def init_cache(cls) -> None:
        """初始化缓存文件"""
        if not cls._CACHE_FILE.exists():
            async with open(file=cls._CACHE_FILE, mode='w', encoding='UTF-8') as file:
                await file.write(
                    dumps({'headers': cls._headers, 'cookies': cls._cookies})
                )

    @classmethod
    async def read_cache(cls) -> None:
        """读取缓存文件"""
        try:
            async with open(file=cls._CACHE_FILE, mode='r', encoding='UTF-8') as file:
                json = loads(await file.read())
        except FileNotFoundError:
            await cls.init_cache()
        except (PermissionError, JSONDecodeError):
            cls._CACHE_FILE.unlink()
            await cls.init_cache()
        else:
            cls._headers = json['headers']
            cls._cookies = json['cookies']

    @classmethod
    async def write_cache(cls) -> None:
        """写入缓存文件"""
        try:
            async with open(file=cls._CACHE_FILE, mode='r+', encoding='UTF-8') as file:
                await file.write(
                    dumps({'headers': cls._headers, 'cookies': cls._cookies})
                )
        except FileNotFoundError:
            await cls.init_cache()
        except (PermissionError, JSONDecodeError):
            cls._CACHE_FILE.unlink()
            await cls.init_cache()

    @classmethod
    async def request(cls, url: str) -> tuple[bool, bool, dict[str, Any]]:
        """请求api"""
        try:
            async with aiohttp.ClientSession(cookies=cls._cookies) as session:
                async with session.get(url, headers=cls._headers) as resp:
                    data = await resp.json()
                    return True, data['success'], data
        except aiohttp.ContentTypeError:
            return await cls._anti_cloudflare(url)
        except aiohttp.ClientError as error:
            logger.error(f'请求错误\n{error}')
            return False, False, {}
