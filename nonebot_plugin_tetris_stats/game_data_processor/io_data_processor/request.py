import os
from typing import Any

import aiohttp
from nonebot import get_driver
from nonebot.log import logger
from playwright.async_api import Browser, Response, async_playwright
from ujson import JSONDecodeError, dumps, loads

from ...utils.config import Config

driver = get_driver()

config = Config.parse_obj(get_driver().config)


@driver.on_startup
async def _():
    await Request.init_cache()
    await Request.read_cache()


@driver.on_shutdown
async def _():
    await Request.close_browser()
    await Request.write_cache()


class Request:
    '''网络请求相关类'''
    _browser: Browser | None = None
    _headers: dict | None = None
    _cookies: dict | None = None

    @classmethod
    async def _init_playwright(cls) -> Browser:
        '''初始化playwright'''
        playwright = await async_playwright().start()
        cls._browser = await playwright.firefox.launch()
        return cls._browser

    @classmethod
    async def _get_browser(cls) -> Browser:
        '''获取浏览器对象'''
        return cls._browser or await cls._init_playwright()

    @classmethod
    async def _anti_cloudflare(cls, url: str) -> tuple[bool, bool, dict[str, Any]]:
        '''用firefox硬穿五秒盾'''
        browser = await cls._get_browser()
        context = await browser.new_context()
        page = await context.new_page()
        response = await page.goto(url)
        attempts = 0
        while attempts < 60:
            attempts += 1
            text = await page.locator("body").text_content()
            if text is None:
                await page.wait_for_timeout(1000)
                continue
            if await page.title() == 'Please Wait... | Cloudflare':
                # TODO 有无人来做一个过验证码（
                break
            try:
                data = loads(text)
            except JSONDecodeError:
                await page.wait_for_timeout(1000)
            else:
                assert isinstance(response, Response)
                cls._headers = await response.request.all_headers()
                try:
                    cls._cookies = {i['name']: i['value'] for i in await context.cookies()}
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
        '''初始化缓存文件'''
        if not os.path.exists(os.path.dirname(config.cache_path)):
            os.makedirs(os.path.dirname(config.cache_path))
        if not os.path.exists(config.cache_path):
            with open(file=config.cache_path, mode='w', encoding='UTF-8') as file:
                file.write(
                    dumps(
                        {
                            'headers': cls._headers,
                            'cookies': cls._cookies
                        }
                    )
                )

    @classmethod
    async def read_cache(cls) -> None:
        '''读取缓存文件'''
        try:
            with open(file=config.cache_path, mode='r', encoding='UTF-8') as file:
                json = loads(file.read())
                cls._headers = json['headers']
                cls._cookies = json['cookies']
        except FileNotFoundError:
            await cls.init_cache()
        except PermissionError:
            os.remove(config.cache_path)
            await cls.init_cache()
        except JSONDecodeError:
            os.remove(config.cache_path)
            await cls.init_cache()

    @classmethod
    async def write_cache(cls) -> None:
        '''写入缓存文件'''
        try:
            with open(file=config.cache_path, mode='r+', encoding='UTF-8') as file:
                file.write(
                    dumps(
                        {
                            'headers': cls._headers,
                            'cookies': cls._cookies
                        }
                    )
                )
        except FileNotFoundError:
            await cls.init_cache()
        except PermissionError:
            os.remove(config.cache_path)
            await cls.init_cache()
        except JSONDecodeError:
            os.remove(config.cache_path)
            await cls.init_cache()

    @classmethod
    async def request(cls, url: str) -> tuple[bool, bool, dict[str, Any]]:
        '''请求api'''
        try:
            async with aiohttp.ClientSession(cookies=cls._cookies) as session:
                async with session.get(url, headers=cls._headers) as resp:
                    data = await resp.json()
                    return True, data['success'], data
        except aiohttp.client_exceptions.ClientConnectorError as error: # type: ignore
            logger.error(f'请求错误\n{error}')
            return False, False, {}
        except aiohttp.client_exceptions.ContentTypeError:  # type: ignore
            return await cls._anti_cloudflare(url)

    @classmethod
    async def close_browser(cls) -> None:
        '''关闭浏览器对象'''
        if isinstance(cls._browser, Browser):
            await cls._browser.close()
