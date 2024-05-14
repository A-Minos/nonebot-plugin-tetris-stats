from typing import Literal, overload

from jinja2 import Environment, FileSystemLoader
from nonebot.compat import PYDANTIC_V2

from ..templates import templates_dir
from .schemas.bind import Bind
from .schemas.tetrio_info import TETRIOInfo

env = Environment(
    loader=FileSystemLoader(templates_dir), autoescape=True, trim_blocks=True, lstrip_blocks=True, enable_async=True
)


@overload
async def render(render_type: Literal['binding'], data: Bind) -> str: ...


@overload
async def render(render_type: Literal['tetrio/info'], data: TETRIOInfo) -> str: ...


async def render(render_type: Literal['binding', 'tetrio/info'], data: Bind | TETRIOInfo) -> str:
    if PYDANTIC_V2:
        return await env.get_template('index.html').render_async(path=render_type, data=data.model_dump_json())
    return await env.get_template('index.html').render_async(path=render_type, data=data.json())


__all__ = ['render', 'Bind', 'TETRIOInfo']
