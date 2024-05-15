from typing import Literal, NamedTuple, overload

from nonebot.compat import type_validate_json

from ....utils.exception import RequestError
from ....utils.request import splice_url
from ..constant import BASE_URL
from .cache import Cache
from .schemas.base import FailedModel
from .schemas.tetra_league import TetraLeague, TetraLeagueSuccess


class FullExport(NamedTuple):
    model: TetraLeagueSuccess
    original: bytes


@overload
async def full_export(*, with_original: Literal[False]) -> TetraLeagueSuccess: ...


@overload
async def full_export(*, with_original: Literal[True]) -> FullExport: ...


async def full_export(*, with_original: bool) -> TetraLeagueSuccess | FullExport:
    full: TetraLeague = type_validate_json(
        TetraLeague,  # type: ignore[arg-type]
        (data := await Cache.get(splice_url([BASE_URL, 'users/lists/league/all']))),
    )
    if isinstance(full, FailedModel):
        msg = f'排行榜数据请求错误:\n{full.error}'
        raise RequestError(msg)
    if with_original:
        return FullExport(full, data)
    return full
