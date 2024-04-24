from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from nonebot import get_app

from ..templates import path

app = get_app()

if not isinstance(app, FastAPI):
    raise RuntimeError('本插件需要 FastAPI 驱动器才能运行')  # noqa: TRY004

app.mount(
    '/static',
    StaticFiles(directory=path),
    name='static',
)
