from typing import Literal, overload

from jinja2 import Environment, FileSystemLoader
from nonebot.compat import PYDANTIC_V2

from ..templates import templates_dir
from .schemas.bind import Bind
from .schemas.tetrio.tetrio_info import Info as TETRIOInfo
from .schemas.tetrio.tetrio_record_blitz import Record as TETRIORecordBlitz
from .schemas.tetrio.tetrio_record_sprint import Record as TETRIORecordSprint
from .schemas.tetrio.tetrio_user_info_v2 import Info as TETRIOUserInfoV2
from .schemas.top_info import Info as TOPInfo
from .schemas.tos_info import Info as TOSInfo

env = Environment(
    loader=FileSystemLoader(templates_dir), autoescape=True, trim_blocks=True, lstrip_blocks=True, enable_async=True
)


@overload
async def render(render_type: Literal['v1/binding'], data: Bind) -> str: ...


@overload
async def render(render_type: Literal['v1/tetrio/info'], data: TETRIOInfo) -> str: ...


@overload
async def render(render_type: Literal['v1/top/info'], data: TOPInfo) -> str: ...


@overload
async def render(render_type: Literal['v1/tos/info'], data: TOSInfo) -> str: ...


@overload
async def render(render_type: Literal['v2/tetrio/user/info'], data: TETRIOUserInfoV2) -> str: ...


@overload
async def render(render_type: Literal['v2/tetrio/record/40l'], data: TETRIORecordSprint) -> str: ...


@overload
async def render(render_type: Literal['v2/tetrio/record/blitz'], data: TETRIORecordBlitz) -> str: ...


async def render(
    render_type: Literal[
        'v1/binding',
        'v1/tetrio/info',
        'v1/top/info',
        'v1/tos/info',
        'v2/tetrio/user/info',
        'v2/tetrio/record/40l',
        'v2/tetrio/record/blitz',
    ],
    data: Bind | TETRIOInfo | TOPInfo | TOSInfo | TETRIOUserInfoV2 | TETRIORecordSprint | TETRIORecordBlitz,
) -> str:
    if PYDANTIC_V2:
        return await env.get_template('index.html').render_async(
            path=render_type, data=data.model_dump_json(by_alias=True)
        )
    return await env.get_template('index.html').render_async(path=render_type, data=data.json(by_alias=True))


__all__ = ['render']
