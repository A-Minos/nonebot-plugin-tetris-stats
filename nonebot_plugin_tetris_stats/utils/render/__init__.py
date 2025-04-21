from typing import Literal, overload

from jinja2 import Environment, FileSystemLoader
from nonebot.compat import PYDANTIC_V2

from ..templates import TEMPLATES_DIR
from .schemas.base import Base
from .schemas.bind import Bind
from .schemas.v1.tetrio.rank import Data as TETRIORankDataV1
from .schemas.v1.tetrio.user.info import Info as TETRIOUserInfoV1
from .schemas.v1.top.info import Info as TOPInfoV1
from .schemas.v1.tos.info import Info as TOSInfoV1
from .schemas.v2.tetrio.rank import Data as TETRIORankDataV2
from .schemas.v2.tetrio.rank.detail import Data as TETRIORankDetailDataV2
from .schemas.v2.tetrio.record.blitz import Record as TETRIORecordBlitzV2
from .schemas.v2.tetrio.record.sprint import Record as TETRIORecordSprintV2
from .schemas.v2.tetrio.tetra_league import Data as TETRIOTetraLeagueDataV2
from .schemas.v2.tetrio.user.info import Info as TETRIOUserInfoV2
from .schemas.v2.tetrio.user.list import List as TETRIOUserListV2

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=False,  # noqa: S701
    trim_blocks=True,
    lstrip_blocks=True,
    enable_async=True,
)


@overload
async def render(render_type: Literal['v1/binding'], data: Bind) -> str: ...
@overload
async def render(render_type: Literal['v1/tetrio/info'], data: TETRIOUserInfoV1) -> str: ...
@overload
async def render(render_type: Literal['v1/tetrio/rank'], data: TETRIORankDataV1) -> str: ...
@overload
async def render(render_type: Literal['v1/top/info'], data: TOPInfoV1) -> str: ...
@overload
async def render(render_type: Literal['v1/tos/info'], data: TOSInfoV1) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/rank'], data: TETRIORankDataV2) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/rank/detail'], data: TETRIORankDetailDataV2) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/record/blitz'], data: TETRIORecordBlitzV2) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/record/sprint'], data: TETRIORecordSprintV2) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/tetra-league'], data: TETRIOTetraLeagueDataV2) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/user/info'], data: TETRIOUserInfoV2) -> str: ...
@overload
async def render(render_type: Literal['v2/tetrio/user/list'], data: TETRIOUserListV2) -> str: ...
async def render(
    render_type: str,
    data: Base,
) -> str:
    if PYDANTIC_V2:
        return await env.get_template('index.html').render_async(
            path=render_type, data=data.model_dump_json(by_alias=True)
        )
    return await env.get_template('index.html').render_async(path=render_type, data=data.json(by_alias=True))


__all__ = ['render']
