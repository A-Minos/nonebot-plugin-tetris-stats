from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from math import floor
from statistics import mean
from typing import TYPE_CHECKING
from uuid import uuid4

from nonebot import get_driver
from nonebot_plugin_alconna import Subcommand
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from ....config.config import config
from ....utils.exception import RequestError
from ....utils.retry import retry
from .. import alc
from .. import command as base_command
from ..api.leaderboards import by
from ..api.schemas.base import P
from ..api.schemas.leaderboards import Parameter
from ..api.schemas.leaderboards.by import Entry
from ..constant import RANK_PERCENTILE
from ..models import TETRIOLeagueHistorical, TETRIOLeagueStats, TETRIOLeagueStatsField

if TYPE_CHECKING:
    from ..api.schemas.leaderboards.by import BySuccessModel
    from ..api.typedefs import Rank

UTC = timezone.utc

driver = get_driver()


command = Subcommand('rank', help_text='查询 TETR.IO 段位信息')


def wrapper(slot: int | str, content: str | None) -> str | None:
    if slot == 'rank' and not content:
        return '--all'
    if content is not None:
        return f'--detail {content.lower()}'
    return content


alc.shortcut(
    r'(?i:io)(?i:段位|段|rank)\s*(?P<rank>[a-zA-Z+-]{0,2})',
    command='tstats TETR.IO rank {rank}',
    humanized='iorank',
    fuzzy=False,
    wrapper=wrapper,
)


def _pps(user: Entry) -> float:
    return user.league.pps


def _apm(user: Entry) -> float:
    return user.league.apm


def _vs(user: Entry) -> float:
    return user.league.vs


def _min(users: Sequence[Entry], field: Callable[[Entry], float]) -> Entry:
    return min(users, key=field)


def _max(users: Sequence[Entry], field: Callable[[Entry], float]) -> Entry:
    return max(users, key=field)


def find_special_player(
    users: Sequence[Entry],
    field: Callable[[Entry], float],
    sort: Callable[[Sequence[Entry], Callable[[Entry], float]], Entry],
) -> Entry:
    return sort(users, field)


@scheduler.scheduled_job('cron', hour='0,6,12,18', minute=0)
async def get_tetra_league_data() -> None:
    x_session_id = uuid4()
    retry_by = retry(max_attempts=10, exception_type=RequestError)(by)
    prisecter = P(pri=9007199254740991, sec=9007199254740991, ter=9007199254740991)  # * from ch.tetr.io
    results: list[BySuccessModel] = []
    while True:
        model = await retry_by('league', Parameter(after=prisecter.to_prisecter(), limit=100), x_session_id)
        prisecter = model.data.entries[-1].p
        results.append(model)
        if len(model.data.entries) < 100:  # 分页值 # noqa: PLR2004
            break

    players: list[Entry] = []
    for result in results:
        players.extend([i for i in result.data.entries if isinstance(i, Entry)])
    players.sort(key=lambda x: x.league.tr, reverse=True)

    rank_player_mapping: defaultdict[Rank, list[Entry]] = defaultdict(list)
    for player in players:
        rank_player_mapping[player.league.rank].append(player)

    stats = TETRIOLeagueStats(raw=[], fields=[], update_time=datetime.now(UTC))
    fields: list[TETRIOLeagueStatsField] = []
    for rank, percentile in RANK_PERCENTILE.items():
        offset = floor((percentile / 100) * len(players)) - 1
        tr_line = players[offset].league.tr
        rank_players = rank_player_mapping[rank]
        fields.append(
            TETRIOLeagueStatsField(
                rank=rank,
                tr_line=tr_line,
                player_count=len(rank_players),
                low_pps=find_special_player(rank_players, _pps, _min),
                low_apm=find_special_player(rank_players, _apm, _min),
                low_vs=find_special_player(rank_players, _vs, _min),
                avg_pps=mean(_pps(i) for i in rank_players),
                avg_apm=mean(_apm(i) for i in rank_players),
                avg_vs=mean(_vs(i) for i in rank_players),
                high_pps=find_special_player(rank_players, _pps, _max),
                high_apm=find_special_player(rank_players, _apm, _max),
                high_vs=find_special_player(rank_players, _vs, _max),
                stats=stats,
            )
        )
    historicals = [
        TETRIOLeagueHistorical(request_id=x_session_id, data=model, update_time=model.cache.cached_at, stats=stats)
        for model in results
    ]
    stats.raw = historicals
    stats.fields = fields
    async with get_session() as session:
        session.add(stats)
        await session.commit()


if not config.tetris.development:

    @driver.on_startup
    async def _() -> None:
        async with get_session() as session:
            latest_time = await session.scalar(
                select(TETRIOLeagueStats.update_time).order_by(TETRIOLeagueStats.id.desc()).limit(1)
            )
        if latest_time is None or datetime.now(tz=UTC) - latest_time.replace(tzinfo=UTC) > timedelta(hours=6):
            await get_tetra_league_data()


from . import all, detail  # noqa: A004, E402

base_command.add(command)

__all__ = ['all', 'detail']
