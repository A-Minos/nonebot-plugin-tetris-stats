from typing import Literal, NamedTuple, overload

from msgspec import Struct, to_builtins
from nonebot.compat import type_validate_json

from ....utils.exception import RequestError
from ..constant import BASE_URL
from .cache import Cache
from .schemas.base import FailedModel
from .schemas.tetra_league import TetraLeague, TetraLeagueSuccess


class Parameter(Struct, omit_defaults=True):
    after: float | None = None
    before: float | None = None
    limit: int | None = None
    country: str | None = None


async def leaderboard(parameter: Parameter | None = None) -> TetraLeagueSuccess:
    league: TetraLeague = type_validate_json(
        TetraLeague,  # type: ignore[arg-type]
        (await Cache.get(BASE_URL / 'users/lists/league' % to_builtins(parameter))),
    )
    if isinstance(league, FailedModel):
        msg = f'排行榜数据请求错误:\n{league.error}'
        raise RequestError(msg)
    return league


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
        (data := await Cache.get(BASE_URL / 'users/lists/league/all')),
    )

    if isinstance(full, FailedModel):
        msg = f'排行榜数据请求错误:\n{full.error}'
        raise RequestError(msg)
    if with_original:
        return FullExport(full, data)
    return full
