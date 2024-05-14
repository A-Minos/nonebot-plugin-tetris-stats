from collections.abc import Sequence
from http import HTTPStatus
from urllib.parse import urljoin, urlparse

from aiofiles import open
from httpx import AsyncClient, HTTPError
from nonebot import get_driver, get_plugin_config
from nonebot.log import logger
from playwright.async_api import Response
from ujson import JSONDecodeError, dumps, loads

from ..config.config import CACHE_PATH, Config
from .browser import BrowserManager
from .exception import RequestError

driver = get_driver()
config = get_plugin_config(Config)


@driver.on_startup
async def _():
    await Request.init_cache()
    await Request.read_cache()


@driver.on_shutdown
async def _():
    await Request.write_cache()


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
                        msg = 'api请求失败'
                        raise RequestError(msg)
                    cls._headers = await response.request.all_headers()
                    try:
                        cls._cookies = {
                            name: value
                            for i in await context.cookies()
                            if (name := i.get('name')) is not None and (value := i.get('value')) is not None
                        }
                    except KeyError:
                        cls._cookies = None
                    return await response.body()
        msg = '绕过五秒盾失败'
        raise RequestError(msg)

    @classmethod
    async def init_cache(cls) -> None:
        """初始化缓存文件"""
        if not cls._CACHE_FILE.exists():
            async with open(file=cls._CACHE_FILE, mode='w', encoding='UTF-8') as file:
                await file.write(dumps({'headers': cls._headers, 'cookies': cls._cookies}))

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
                await file.write(dumps({'headers': cls._headers, 'cookies': cls._cookies}))
        except FileNotFoundError:
            await cls.init_cache()
        except (PermissionError, JSONDecodeError):
            cls._CACHE_FILE.unlink()
            await cls.init_cache()

    @classmethod
    async def request(cls, url: str, *, is_json: bool = True) -> bytes:
        """请求api"""
        try:
            async with AsyncClient(cookies=cls._cookies, timeout=config.tetris_req_timeout) as session:
                response = await session.get(url, headers=cls._headers)
                if response.status_code != HTTPStatus.OK:
                    msg = f'请求错误 code: {response.status_code} {HTTPStatus(response.status_code).phrase}\n{response.text}'
                    raise RequestError(msg, status_code=response.status_code)
                if is_json:
                    loads(response.content)
                return response.content
        except HTTPError as e:
            msg = f'请求错误 \n{e!r}'
            raise RequestError(msg) from e
        except JSONDecodeError:
            if urlparse(url).netloc.lower().endswith('tetr.io'):
                return await cls._anti_cloudflare(url)
            raise

    @classmethod
    async def failover_request(
        cls,
        urls: Sequence[str],
        *,
        failover_code: Sequence[int],
        failover_exc: tuple[type[BaseException], ...],
        is_json: bool = True,
    ) -> bytes:
        error_list: list[RequestError] = []
        for i in urls:
            logger.debug(f'尝试请求 {i}')
            try:
                return await cls.request(i, is_json=is_json)
            except RequestError as e:
                if e.status_code in failover_code:  # 如果状态码在 failover_code 中, 则继续尝试下一个URL
                    error_list.append(e)
                    continue
                # 如果状态码不在故障转移列表中, 则查找异常栈, 如果异常栈内有 failover_exc 内的异常类型, 则继续尝试下一个URL
                tb = e.__traceback__
                while tb is not None:
                    if isinstance(tb.tb_frame.f_locals.get('exc_value'), failover_exc):
                        error_list.append(e)
                        break
                    tb = tb.tb_next
                else:
                    raise
                continue
        msg = f'所有地址皆不可用\n{error_list!r}'
        raise RequestError(msg)
