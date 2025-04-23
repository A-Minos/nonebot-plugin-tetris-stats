from collections.abc import Callable
from datetime import timedelta
from typing import TypeVar, overload
from zoneinfo import ZoneInfo

from ....utils.exception import FallbackError
from ....utils.render.schemas.base import HistoryData
from ..api.schemas.labs.leagueflow import Empty, LeagueFlowSuccess
from ..api.schemas.summaries.league import InvalidData, LeagueSuccessModel, NeverPlayedData, NeverRatedData, RatedData


def flow_to_history(
    leagueflow: LeagueFlowSuccess,
    handle: Callable[[list[HistoryData]], list[HistoryData]] | None = None,
) -> list[HistoryData]:
    if isinstance(leagueflow.data, Empty):
        raise FallbackError
    start_time = leagueflow.data.start_time.astimezone(ZoneInfo('Asia/Shanghai'))
    ret = [
        HistoryData(
            record_at=start_time + timedelta(milliseconds=i.timestamp_offset),
            score=i.post_match_tr,
        )
        for i in leagueflow.data.points
        if start_time + timedelta(milliseconds=i.timestamp_offset)
    ]
    return ret if handle is None else handle(ret)


N = TypeVar('N', int, float)


def handling_special_value(value: N) -> N | None:
    return value if value != -1 else None


L = TypeVar('L', NeverPlayedData, NeverRatedData, RatedData)


@overload
def get_league_data(user_info: LeagueSuccessModel, league_type: type[L]) -> L: ...
@overload
def get_league_data(
    user_info: LeagueSuccessModel, league_type: None = None
) -> NeverPlayedData | NeverRatedData | RatedData: ...
def get_league_data(
    user_info: LeagueSuccessModel, league_type: type[L] | None = None
) -> L | NeverPlayedData | NeverRatedData | RatedData:
    league = user_info.data
    if isinstance(league, InvalidData):
        raise FallbackError
    if league_type is None:
        return league
    if isinstance(league, league_type):
        return league
    raise FallbackError
