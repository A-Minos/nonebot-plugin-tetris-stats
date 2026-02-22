from asyncio import gather
from datetime import datetime, timedelta, timezone
from hashlib import md5
from typing import Literal, NamedTuple

from nonebot_plugin_orm import AsyncSession, get_session
from sqlalchemy import func, select
from yarl import URL

from ....utils.chart import get_split, get_value_bounds, handle_history_data
from ....utils.host import get_self_netloc
from ....utils.lang import get_lang
from ....utils.metrics import TetrisMetricsProWithPPSVS, get_metrics
from ....utils.render import render_image
from ....utils.render.schemas.base import Avatar, Trending
from ....utils.render.schemas.v1.base import History
from ....utils.render.schemas.v1.tetrio.info import Info, Multiplayer, Singleplayer, User
from ..api import Player
from ..api.models import TETRIOHistoricalData
from ..api.schemas.leaderboards.by import Entry, InvalidEntry
from ..api.schemas.summaries.league import LeagueSuccessModel, NeverRatedData, RatedData
from ..constant import TR_MAX, TR_MIN
from ..models import TETRIOLeagueHistorical, TETRIOLeagueUserMap, TETRIOUserUniqueIdentifier
from .tools import flow_to_history, get_league_data

UTC = timezone.utc


class Trends(NamedTuple):
    pps: Trending = Trending.KEEP
    apm: Trending = Trending.KEEP
    adpm: Trending = Trending.KEEP


class HistoricalSnapshot(NamedTuple):
    metrics: TetrisMetricsProWithPPSVS
    delta: timedelta


async def get_nearest_historical(
    session: AsyncSession,
    unique_identifier: str,
    target_time: datetime,
) -> HistoricalSnapshot | None:
    before = await session.scalar(
        select(TETRIOHistoricalData)
        .where(
            TETRIOHistoricalData.user_unique_identifier == unique_identifier,
            TETRIOHistoricalData.api_type == 'league',
            TETRIOHistoricalData.update_time <= target_time,
        )
        .order_by(TETRIOHistoricalData.update_time.desc())
        .limit(1)
    )
    after = await session.scalar(
        select(TETRIOHistoricalData)
        .where(
            TETRIOHistoricalData.user_unique_identifier == unique_identifier,
            TETRIOHistoricalData.api_type == 'league',
            TETRIOHistoricalData.update_time >= target_time,
        )
        .order_by(TETRIOHistoricalData.update_time.asc())
        .limit(1)
    )
    candidates = [i for i in (before, after) if i is not None]
    if not candidates:
        return None

    delta_seconds, selected = min(
        (
            abs((target_time - i.update_time.astimezone(UTC)).total_seconds()),
            i,
        )
        for i in candidates
    )
    delta = timedelta(seconds=delta_seconds)

    if not isinstance(selected.data, LeagueSuccessModel) or not isinstance(
        selected.data.data, RatedData | NeverRatedData
    ):
        return None

    data = selected.data.data
    return HistoricalSnapshot(get_metrics(pps=data.pps, apm=data.apm, vs=data.vs), delta)


async def _get_boundary_league_historical(
    session: AsyncSession,
    uid_id: int,
    target_time: datetime,
    *,
    time_direction: Literal['before', 'after'],
) -> tuple[TETRIOLeagueUserMap, datetime] | None:
    boundary_time = await session.scalar(
        select((func.max if time_direction == 'before' else func.min)(TETRIOLeagueHistorical.update_time))
        .select_from(TETRIOLeagueUserMap)
        .join(TETRIOLeagueHistorical, TETRIOLeagueUserMap.hist_id == TETRIOLeagueHistorical.id)
        .where(
            TETRIOLeagueUserMap.uid_id == uid_id,
            TETRIOLeagueHistorical.update_time <= target_time
            if time_direction == 'before'
            else TETRIOLeagueHistorical.update_time >= target_time,
        )
    )
    if boundary_time is None:
        return None

    return (
        (
            await session.execute(
                select(TETRIOLeagueUserMap, TETRIOLeagueHistorical.update_time)
                .join(TETRIOLeagueHistorical, TETRIOLeagueUserMap.hist_id == TETRIOLeagueHistorical.id)
                .where(
                    TETRIOLeagueUserMap.uid_id == uid_id,
                    TETRIOLeagueHistorical.update_time == boundary_time,
                )
                .order_by(TETRIOLeagueHistorical.id.desc())
                .limit(1)
            )
        )
        .tuples()
        .first()
    )


async def get_nearest_league_historical(
    session: AsyncSession,
    unique_identifier: str,
    target_time: datetime,
) -> HistoricalSnapshot | None:
    uid_id = await session.scalar(
        select(TETRIOUserUniqueIdentifier.id).where(
            TETRIOUserUniqueIdentifier.user_unique_identifier == unique_identifier
        )
    )
    if uid_id is None:
        return None

    before = await _get_boundary_league_historical(
        session,
        uid_id,
        target_time,
        time_direction='before',
    )
    after = await _get_boundary_league_historical(
        session,
        uid_id,
        target_time,
        time_direction='after',
    )

    candidates = [i for i in (before, after) if i is not None]
    if not candidates:
        return None
    delta_seconds, selected = min(
        (
            abs((target_time - i[1].astimezone(UTC)).total_seconds()),
            i[0],
        )
        for i in candidates
    )
    delta = timedelta(seconds=delta_seconds)

    historical = await session.get(TETRIOLeagueHistorical, selected.hist_id)
    if historical is None or not isinstance(
        (entry := find_entry(historical.data.data.entries, selected.entry_index, unique_identifier)), Entry
    ):
        return None
    return HistoricalSnapshot(get_metrics(pps=entry.league.pps, apm=entry.league.apm, vs=entry.league.vs), delta)


def find_entry(
    entries: list[Entry | InvalidEntry],
    entry_index: int,
    unique_identifier: str | None = None,
) -> Entry | InvalidEntry | None:
    if 0 <= entry_index < len(entries):
        entry = entries[entry_index]
        if unique_identifier is None or entry.id == unique_identifier:
            return entry
    if unique_identifier is None:
        return None
    for entry in entries:
        if entry.id == unique_identifier:
            return entry
    return None


async def get_trends(player: Player, compare_delta: timedelta) -> Trends:
    league = await player.league
    if not isinstance(league.data, RatedData | NeverRatedData):
        return Trends()
    user = await player.user

    async with get_session() as session:
        target_time = (league.cache.cached_at - compare_delta).astimezone(UTC)
        historical, league_historical = await gather(
            get_nearest_historical(
                session,
                user.unique_identifier,
                target_time,
            ),
            get_nearest_league_historical(
                session,
                user.unique_identifier,
                target_time,
            ),
        )
    selected = min((historical, league_historical), key=lambda x: x.delta if x is not None else timedelta.max)
    if selected is None:
        return Trends()
    metrics = get_metrics(pps=league.data.pps, apm=league.data.apm, vs=league.data.vs)
    return Trends(
        pps=Trending.compare(selected.metrics.pps, metrics.pps),
        apm=Trending.compare(selected.metrics.apm, metrics.apm),
        adpm=Trending.compare(selected.metrics.adpm, metrics.adpm),
    )


async def make_query_image_v1(player: Player, compare_delta: timedelta) -> bytes:
    (
        (user, user_info, league, sprint, blitz, leagueflow),
        (avatar_revision,),
    ) = await gather(
        gather(player.user, player.get_info(), player.league, player.sprint, player.blitz, player.get_leagueflow()),
        gather(player.avatar_revision),
    )
    league_data = get_league_data(league, RatedData)
    histories = flow_to_history(leagueflow, handle_history_data)
    values = get_value_bounds([i.score for i in histories])
    split_value, offset = get_split(values, TR_MAX, TR_MIN)
    if sprint.data.record is not None:
        duration = timedelta(milliseconds=sprint.data.record.results.stats.finaltime).total_seconds()
        sprint_value = f'{duration:.3f}s' if duration < 60 else f'{duration // 60:.0f}m {duration % 60:.3f}s'  # noqa: PLR2004
    else:
        sprint_value = 'N/A'
    blitz_value = f'{blitz.data.record.results.stats.score:,}' if blitz.data.record is not None else 'N/A'
    dsps: float
    dspp: float
    # make mypy happy
    return await render_image(
        Info(
            user=User(
                avatar=str(
                    URL(f'http://{get_self_netloc()}/host/resource/tetrio/avatars/{user.ID}')
                    % {'revision': avatar_revision}
                )
                if avatar_revision is not None and avatar_revision != 0
                else Avatar(
                    type='identicon',
                    hash=md5(user.ID.encode()).hexdigest(),  # noqa: S324
                ),
                name=user.name.upper(),
                bio=user_info.data.bio,
            ),
            multiplayer=Multiplayer(
                glicko=f'{round(league_data.glicko, 2):,}',
                rd=round(league_data.rd, 2),
                rank=league_data.rank,
                tr=f'{round(league_data.tr, 2):,}',
                global_rank=league_data.standing,
                history=History(
                    data=histories,
                    split_interval=split_value,
                    min_value=values.value_min,
                    max_value=values.value_max,
                    offset=offset,
                ),
                lpm=(metrics := get_metrics(pps=league_data.pps, apm=league_data.apm, vs=league_data.vs)).lpm,
                pps=metrics.pps,
                lpm_trending=(trends := (await get_trends(player, compare_delta))).pps,
                apm=metrics.apm,
                apl=metrics.apl,
                apm_trending=trends.apm,
                adpm=metrics.adpm,
                vs=metrics.vs,
                adpl=metrics.adpl,
                adpm_trending=trends.adpm,
                app=(app := (league_data.apm / (60 * league_data.pps))),
                dsps=(dsps := ((league_data.vs / 100) - (league_data.apm / 60))),
                dspp=(dspp := (dsps / league_data.pps)),
                ci=150 * dspp - 125 * app + 50 * (league_data.vs / league_data.apm) - 25,
                ge=2 * ((app * dsps) / league_data.pps),
            ),
            singleplayer=Singleplayer(
                sprint=sprint_value,
                blitz=blitz_value,
            ),
            lang=get_lang(),
        ),
    )
