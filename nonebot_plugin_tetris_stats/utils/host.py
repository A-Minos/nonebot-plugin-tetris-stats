from functools import cache
from hashlib import sha256
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path as FilePath
from typing import TYPE_CHECKING, Annotated, ClassVar, Literal

from aiofiles import open as aopen
from fastapi import BackgroundTasks, FastAPI, Path, status
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from nonebot import get_app, get_driver
from nonebot.log import logger
from yarl import URL

from ..config.config import CACHE_PATH, config
from ..games.tetrio.api.cache import request
from .image import img_to_png
from .templates import TEMPLATES_DIR

if TYPE_CHECKING:
    from pydantic import IPvAnyAddress

app: FastAPI = get_app()

driver = get_driver()

global_config = driver.config

BASE_URL = URL('https://tetr.io/user-content/')

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

    if not config.tetris.development:

        async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            self.pages.pop(self.page_hash, None)
    else:

        async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            pass


@driver.on_startup
def _():
    app.mount(
        '/host/_nuxt',
        StaticFiles(directory=TEMPLATES_DIR / '_nuxt'),
        name='assets',
    )
    logger.success('assets mounted')


@app.get('/host/{page_hash}.html', status_code=status.HTTP_200_OK)
def _(page_hash: str) -> HTMLResponse:
    if page_hash in HostPage.pages:
        return HTMLResponse(HostPage.pages[page_hash])
    return NOT_FOUND


@app.get('/host/resource/tetrio/{resource_type}/{user_id}', status_code=status.HTTP_200_OK)
async def _(
    resource_type: Literal['avatars', 'banners'],
    user_id: Annotated[str, Path(regex=r'^[a-f0-9]{24}$')],
    revision: int,
    background_tasks: BackgroundTasks,
) -> Response:
    if not (path := CACHE_PATH / 'tetrio' / resource_type / f'{user_id}_{revision}.png').exists():
        image = img_to_png(
            await request.request(
                BASE_URL / resource_type / f'{user_id}.jpg' % {'rv': revision},
                is_json=False,
            )
        )
        background_tasks.add_task(write_cache, path=path, data=image)
        return Response(content=image, media_type='image/png')
    return FileResponse(path)


async def write_cache(path: FilePath, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aopen(path, 'wb') as file:
        await file.write(data)


@cache
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
