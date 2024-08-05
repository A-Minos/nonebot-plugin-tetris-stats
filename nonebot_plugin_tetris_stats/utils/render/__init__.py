from typing import Literal, overload

from jinja2 import Environment, FileSystemLoader
from nonebot.compat import PYDANTIC_V2

from ..templates import TEMPLATES_DIR
from .schemas.bind import Bind
from .schemas.tetrio.rank.detail import Data as TETRIORankDetailData
from .schemas.tetrio.rank.v1 import Data as TETRIORankDataV1
from .schemas.tetrio.rank.v2 import Data as TETRIORankDataV2
from .schemas.tetrio.record.blitz import Record as TETRIORecordBlitz
from .schemas.tetrio.record.sprint import Record as TETRIORecordSprint
from .schemas.tetrio.user.info_v1 import Info as TETRIOUserInfoV1
from .schemas.tetrio.user.info_v2 import Info as TETRIOUserInfoV2
from .schemas.tetrio.user.list_v2 import List as TETRIOUserListV2
from .schemas.top_info import Info as TOPInfo
from .schemas.tos_info import Info as TOSInfo

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True, trim_blocks=True, lstrip_blocks=True, enable_async=True
)


@overload
async def render(render_type: Literal['v1/binding'], data: Bind) -> str: ...
@overload
async def render(render_type: Literal['v1/tetrio/info'], data: TETRIOUserInfoV1) -> str: ...
@overload
async def render(render_type: Literal['v1/tetrio/rank'], data: TETRIORankDataV1) -> str: ...
@overload
async def render(render_type: Literal['v1/top/info'], data: TOPInfo) -> str: ...
@overload
async def render(render_type: Literal['v1/tos/info'], data: TOSInfo) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/user/info'], data: TETRIOUserInfoV2) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/user/list'], data: TETRIOUserListV2) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/record/40l'], data: TETRIORecordSprint) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/record/blitz'], data: TETRIORecordBlitz) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/rank'], data: TETRIORankDataV2) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/rank/detail'], data: TETRIORankDetailData) -> str: ...


async def render(
    render_type: Literal[
        'v1/binding',
        'v1/tetrio/info',
        'v1/tetrio/rank',
        'v1/top/info',
        'v1/tos/info',
        'v2/tetrio/user/info',
        'v2/tetrio/user/list',
        'v2/tetrio/record/40l',
        'v2/tetrio/record/blitz',
        'v2/tetrio/rank',
        'v2/tetrio/rank/detail',
    ],
    data: Bind
    | TETRIOUserInfoV1
    | TETRIORankDataV1
    | TOPInfo
    | TOSInfo
    | TETRIOUserInfoV2
    | TETRIOUserListV2
    | TETRIORecordSprint
    | TETRIORecordBlitz
    | TETRIORankDataV2
    | TETRIORankDetailData,
) -> str:
    if PYDANTIC_V2:
        return await env.get_template('index.html').render_async(
            path=render_type, data=data.model_dump_json(by_alias=True)
        )
    return await env.get_template('index.html').render_async(path=render_type, data=data.json(by_alias=True))


__all__ = ['render']
