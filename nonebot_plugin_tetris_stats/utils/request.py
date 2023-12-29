from http import HTTPStatus
from urllib.parse import urljoin, urlparse

from aiofiles import open
from httpx import AsyncClient, HTTPError
from nonebot import get_driver
from nonebot.log import logger
from playwright.async_api import Response
from ujson import JSONDecodeError, dumps, loads

from ..config.config import CACHE_PATH, Config
from .browser import BrowserManager
from .exception import RequestError

driver = get_driver()
config = Config.parse_obj(driver.config)


@driver.on_startup
async def _():
    await Request._init_cache()
    await Request._read_cache()


@driver.on_shutdown
async def _():
    await Request._write_cache()


def splice_url(url_list: list[str]) -> str:
    url = ''
    if len(url_list):
        url = url_list.pop(0)
        for i in url_list:
            url = urljoin(url, i)
    return url


class Request:
    """网络请求相关类"""

    _CACHE_FILE = CACHE_PATH / 'cloudflare_cache.json'
    _headers: dict | None = None
    _cookies: dict | None = None

    @classmethod
    async def _anti_cloudflare(cls, url: str) -> bytes:
        """用firefox硬穿五秒盾"""
        browser = await BrowserManager.get_browser()
        async with await browser.new_context() as context, await context.new_page() as page:
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
                    loads(text)
                except JSONDecodeError:
                    await page.wait_for_timeout(1000)
                else:
                    if not isinstance(response, Response):
                        raise RequestError('api请求失败')
                    cls._headers = await response.request.all_headers()
                    try:
                        cls._cookies = {i['name']: i['value'] for i in await context.cookies()}
                    except KeyError:
                        cls._cookies = None
                    return await response.body()
        raise RequestError('绕过五秒盾失败')

    @classmethod
    async def _init_cache(cls) -> None:
        """初始化缓存文件"""
        if not cls._CACHE_FILE.exists():
            async with open(file=cls._CACHE_FILE, mode='w', encoding='UTF-8') as file:
                await file.write(dumps({'headers': cls._headers, 'cookies': cls._cookies}))

    @classmethod
    async def _read_cache(cls) -> None:
        """读取缓存文件"""
        try:
            async with open(file=cls._CACHE_FILE, mode='r', encoding='UTF-8') as file:
                json = loads(await file.read())
        except FileNotFoundError:
            await cls._init_cache()
        except (PermissionError, JSONDecodeError):
            cls._CACHE_FILE.unlink()
            await cls._init_cache()
        else:
            cls._headers = json['headers']
            cls._cookies = json['cookies']

    @classmethod
    async def _write_cache(cls) -> None:
        """写入缓存文件"""
        try:
            async with open(file=cls._CACHE_FILE, mode='r+', encoding='UTF-8') as file:
                await file.write(dumps({'headers': cls._headers, 'cookies': cls._cookies}))
        except FileNotFoundError:
            await cls._init_cache()
        except (PermissionError, JSONDecodeError):
            cls._CACHE_FILE.unlink()
            await cls._init_cache()

    @classmethod
    async def request(cls, url: str, *, is_json: bool = True) -> bytes:
        """请求api"""
        try:
            async with AsyncClient(cookies=cls._cookies, timeout=config.tetris_req_timeout) as session:
                response = await session.get(url, headers=cls._headers)
                if response.status_code != HTTPStatus.OK:
                    raise RequestError(
                        f'请求错误 code: {response.status_code} {HTTPStatus(response.status_code).phrase}\n{response.text}'
                    )
                if is_json:
                    loads(response.content)
                return response.content
        except HTTPError as e:
            raise RequestError(f'请求错误 \n{e!r}') from e
        except JSONDecodeError:
            if urlparse(url).netloc.lower().endswith('tetr.io'):
                return await cls._anti_cloudflare(url)
            raise
