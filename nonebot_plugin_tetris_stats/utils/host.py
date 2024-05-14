from hashlib import sha256
from ipaddress import IPv4Address, IPv6Address
from typing import TYPE_CHECKING, ClassVar

from fastapi import FastAPI, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from nonebot import get_app, get_driver
from nonebot.log import logger
from nonebot_plugin_localstore import get_cache_dir  # type: ignore[import-untyped]

from .templates import templates_dir

if TYPE_CHECKING:
    from pydantic import IPvAnyAddress

app = get_app()

driver = get_driver()

global_config = driver.config

cache_dir = get_cache_dir('nonebot_plugin_tetris_stats')

if not isinstance(app, FastAPI):
    msg = '本插件需要 FastAPI 驱动器才能运行'
    raise RuntimeError(msg)  # noqa: TRY004

NOT_FOUND = HTMLResponse('404 Not Found', status_code=status.HTTP_404_NOT_FOUND)


class HostPage:
    pages: ClassVar[dict[str, str]] = {}

    def __init__(self, page: str) -> None:
        self.page_hash = sha256(page.encode()).hexdigest()
        self.pages[self.page_hash] = page

    async def __aenter__(self) -> str:
        return self.page_hash

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.pages.pop(self.page_hash, None)


@driver.on_startup
def _():
    app.mount(
        '/host/assets',
        StaticFiles(directory=templates_dir / 'assets'),
        name='assets',
    )
    logger.success('assets mounted')


@app.get('/host/{page_hash}.html', status_code=status.HTTP_200_OK)
async def _(page_hash: str) -> HTMLResponse:
    if page_hash in HostPage.pages:
        return HTMLResponse(HostPage.pages[page_hash])
    return NOT_FOUND


def get_self_netloc() -> str:
    host: IPv4Address | IPv6Address | IPvAnyAddress = global_config.host
    if isinstance(host, IPv4Address):
        if host == IPv4Address('0.0.0.0'):  # noqa: S104
            host = IPv4Address('127.0.0.1')
        netloc = f'{host}:{global_config.port}'
    else:
        if host == IPv6Address('::'):
            host = IPv6Address('::1')
        netloc = f'[{host}]:{global_config.port}'
    return netloc
