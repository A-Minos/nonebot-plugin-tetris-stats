from collections.abc import Sequence
from http import HTTPStatus
from typing import Any

from fake_useragent import UserAgent
from httpx import AsyncClient, HTTPError
from msgspec import DecodeError, Struct, json
from nonebot import get_driver
from nonebot.log import logger
from playwright.async_api import Response
from yarl import URL

from ..config.config import CACHE_PATH, config
from .browser import BrowserManager
from .exception import RequestError

driver = get_driver()


class CloudflareCache(Struct):
    headers: dict[str, Any] | None = None
    cookies: dict[str, Any] | None = None


encoder = json.Encoder()
decoder = json.Decoder()


class AntiCloudflare:
    cache_decoder = json.Decoder(type=CloudflareCache)

    def __init__(self, domain_suffix: str) -> None:
        self.domain_suffix = domain_suffix
        self.cache_path = CACHE_PATH / f'{self.domain_suffix}_cloudflare_cache.json'
        self._headers: dict | None = None
        self._cookies: dict | None = None
        self.read_cache()

    def read_cache(self) -> None:
        """读取缓存文件"""
        try:
            cache: CloudflareCache = self.cache_decoder.decode(self.cache_path.read_text(encoding='UTF-8'))
            self._headers = cache.headers
            self._cookies = cache.cookies
        except (OSError, DecodeError):
            self.cache_path.unlink()
            self.write_cache()

    def write_cache(self) -> None:
        """写入缓存文件"""
        self.cache_path.write_bytes(json.encode(CloudflareCache(headers=self.headers, cookies=self.cookies)))

    @property
    def headers(self) -> dict | None:
        return self._headers

    @headers.setter
    def headers(self, value: dict | None) -> None:
        self._headers = value
        self.write_cache()

    @property
    def cookies(self) -> dict | None:
        return self._cookies

    @cookies.setter
    def cookies(self, value: dict | None) -> None:
        self._cookies = value
        self.write_cache()

    async def __call__(self, url: str, proxy: str | None = None) -> bytes:
        """用firefox硬穿五秒盾"""
        browser = await BrowserManager.get_browser()
        async with (
            await browser.new_context(proxy={'server': proxy} if proxy is not None else None) as context,
            await context.new_page() as page,
        ):
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
                    decoder.decode(text)
                except DecodeError:
                    await page.wait_for_timeout(1000)
                else:
                    if not isinstance(response, Response):
                        msg = 'api请求失败'
                        raise RequestError(msg)
                    self.headers = await response.request.all_headers()
                    try:
                        self.cookies = {
                            name: value
                            for i in await context.cookies()
                            if (name := i.get('name')) is not None and (value := i.get('value')) is not None
                        }
                    except KeyError:
                        self.cookies = None
                    return await response.body()
        msg = '绕过五秒盾失败'
        raise RequestError(msg)


class Request:
    """网络请求相关类"""

    def __init__(self, proxy: str | None) -> None:
        self.proxy = proxy
        self.anti_cloudflares: dict[str, AntiCloudflare] = {}
        self.client = AsyncClient(timeout=config.tetris.request_timeout, proxy=self.proxy)
        self.ua = UserAgent()

    async def request(
        self,
        url: URL,
        extra_headers: dict | None = None,
        *,
        is_json: bool = True,
        enable_anti_cloudflare: bool = False,
    ) -> bytes:
        """请求api"""
        if (anti_cloudflare := self.anti_cloudflares.get(url.host or '')) is not None:
            cookies = anti_cloudflare.cookies
            headers = anti_cloudflare.headers
        else:
            cookies = None
            headers = None
        if headers is None:
            headers = {}
        if extra_headers:
            headers.update(extra_headers)
        headers.setdefault('User-Agent', self.ua.random)
        try:
            response = await self.client.get(str(url), cookies=cookies, headers=headers)
            if response.status_code != HTTPStatus.OK:
                msg = (
                    f'请求错误 code: {response.status_code} {HTTPStatus(response.status_code).phrase}\n{response.text}'
                )
                raise RequestError(msg, status_code=response.status_code)
            if is_json:
                decoder.decode(response.content)
        except HTTPError as e:
            msg = f'请求错误 \n{e!r}'
            raise RequestError(msg) from e
        except DecodeError:  # 由于捕获的是 DecodeError 所以一定是 is_json = True
            if enable_anti_cloudflare and url.host is not None:
                return await self.anti_cloudflares.setdefault(url.host, AntiCloudflare(url.host))(str(url), self.proxy)
            raise
        else:
            return response.content

    async def failover_request(
        self,
        urls: Sequence[URL],
        *,
        failover_code: Sequence[int],
        failover_exc: tuple[type[BaseException], ...],
        is_json: bool = True,
    ) -> bytes:
        error_list: list[RequestError] = []
        for i in urls:
            logger.debug(f'尝试请求 {i}')
            try:
                return await self.request(i, is_json=is_json)
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
