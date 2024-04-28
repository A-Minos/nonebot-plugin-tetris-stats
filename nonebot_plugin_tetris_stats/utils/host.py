from hashlib import sha256
from typing import ClassVar

from fastapi import FastAPI, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from nonebot import get_app

from ..templates import path

app = get_app()

if not isinstance(app, FastAPI):
    raise RuntimeError('本插件需要 FastAPI 驱动器才能运行')  # noqa: TRY004


class HostPage:
    pages: ClassVar[dict[str, str]] = {}

    def __init__(self, page: str) -> None:
        self.page_hash = sha256(page.encode()).hexdigest()
        self.pages[self.page_hash] = page

    async def __aenter__(self) -> str:
        return self.page_hash

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.pages.pop(self.page_hash, None)


app.mount(
    '/static',
    StaticFiles(directory=path),
    name='static',
)


@app.get('/host/{page_hash}.html', status_code=status.HTTP_200_OK)
async def _(page_hash: str) -> HTMLResponse:
    if page_hash in HostPage.pages:
        return HTMLResponse(HostPage.pages[page_hash])
    return HTMLResponse('404 Not Found', status_code=status.HTTP_404_NOT_FOUND)
