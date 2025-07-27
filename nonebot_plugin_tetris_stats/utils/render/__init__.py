from jinja2 import Environment, FileSystemLoader
from nonebot.compat import PYDANTIC_V2

from ..host import HostPage, get_self_netloc
from ..screenshot import screenshot
from ..templates import TEMPLATES_DIR
from .schemas.base import Base

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=False,  # noqa: S701
    trim_blocks=True,
    lstrip_blocks=True,
    enable_async=True,
)


async def render(
    data: Base,
) -> str:
    if PYDANTIC_V2:
        return await env.get_template('index.html').render_async(data=data.model_dump_json(by_alias=True))
    return await env.get_template('index.html').render_async(data=data.json(by_alias=True))


async def render_image(
    data: Base,
) -> bytes:
    async with HostPage(page=await render(data)) as page_hash:
        return await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html#/{data.path}')


__all__ = ['render']
