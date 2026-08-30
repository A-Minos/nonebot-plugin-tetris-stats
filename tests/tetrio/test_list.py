from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.leaderboards.by import Entry, InvalidEntry
    from nonebot_plugin_tetris_stats.games.tetrio.models import TETRIOLeagueStats
    from nonebot_plugin_tetris_stats.games.tetrio.rank.snapshot import ListSort


UTC = timezone.utc


@dataclass(frozen=True)
class MetricCase:
    sort: 'ListSort'
    pps: float
    apm: float
    vs: float
    expected_first: str


@pytest.fixture
async def league_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    from nonebot_plugin_tetris_stats.games.tetrio.models import (  # noqa: PLC0415
        TETRIOLeagueHistorical,
        TETRIOLeagueStats,
    )

    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: TETRIOLeagueStats.metadata.create_all(
                sync_conn,
                tables=[TETRIOLeagueStats.__table__, TETRIOLeagueHistorical.__table__],
            )
        )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def make_entry(
    user_id: str,
    *,
    tr: float,
    pps: float = 2.0,
    apm: float = 40.0,
    vs: float = 80.0,
) -> 'Entry':
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base import ArCounts, P  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.leaderboards.by import (  # noqa: PLC0415
        Entry,
        League,
    )

    return Entry(
        _id=user_id,
        username=user_id,
        role='user',
        ts=None,
        xp=0.0,
        country='US',
        supporter=None,
        gamesplayed=10,
        gameswon=6,
        gametime=1.0,
        ar=0,
        ar_counts=ArCounts(),
        p=P(pri=tr, sec=0.0, ter=0.0),
        league=League(
            gamesplayed=10,
            gameswon=6,
            tr=tr,
            gxe=0.5,
            rank='s',
            bestrank='s',
            glicko=1500.0,
            rd=50.0,
            decaying=False,
            pps=pps,
            apm=apm,
            vs=vs,
        ),
    )


def make_snapshot(entries: Sequence['Entry'], *, when: datetime, request_id: int) -> 'TETRIOLeagueStats':
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base import Cache  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.leaderboards.by import (  # noqa: PLC0415
        BySuccessModel,
        Data,
    )
    from nonebot_plugin_tetris_stats.games.tetrio.models import (  # noqa: PLC0415
        TETRIOLeagueHistorical,
        TETRIOLeagueStats,
    )

    persisted_entries: list[Entry | InvalidEntry] = []
    persisted_entries.extend(entries)
    stats = TETRIOLeagueStats(raw=[], fields=[], update_time=when)
    historical = TETRIOLeagueHistorical(
        request_id=UUID(int=request_id),
        data=BySuccessModel(
            success=True,
            cache=Cache(status='cached', cached_at=when, cached_until=when + timedelta(minutes=5)),
            data=Data(entries=persisted_entries),
        ),
        update_time=when,
        stats=stats,
    )
    stats.raw = [historical]
    return stats


@pytest.mark.parametrize('sort', ['league', 'pps', 'apm', 'adpm', 'apl', 'adpl'])
def test_list_accepts_all_sort_values(sort: str) -> None:
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415

    result = command.parse(f'tstats TETR.IO list --sort {sort}')

    assert result.matched  # noqa: S101
    assert result.all_matched_args['sort'] == sort  # noqa: S101


def test_list_defaults_to_league_sort() -> None:
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415

    result = command.parse('tstats TETR.IO list')

    assert result.matched  # noqa: S101
    assert 'sort' not in result.all_matched_args  # noqa: S101


@pytest.mark.asyncio
async def test_league_list_defaults_to_descending_league_order(
    league_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.rank.snapshot import (  # noqa: PLC0415
        LeagueListQuery,
        query_league_list,
    )

    async with league_sessionmaker() as session:
        session.add(
            make_snapshot(
                [make_entry('lower', tr=12000), make_entry('higher', tr=18000)],
                when=datetime(2026, 8, 30, tzinfo=UTC),
                request_id=1,
            )
        )
        await session.commit()

    async with league_sessionmaker() as session:
        entries = await query_league_list(session, LeagueListQuery())

    assert [entry.id for entry in entries] == ['higher', 'lower']  # noqa: S101


@pytest.mark.asyncio
async def test_league_list_min_tr_returns_window_closest_to_lower_bound(
    league_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.rank.snapshot import (  # noqa: PLC0415
        LeagueListQuery,
        query_league_list,
    )

    async with league_sessionmaker() as session:
        session.add(
            make_snapshot(
                [
                    make_entry('highest', tr=18000),
                    make_entry('nearest', tr=11000),
                    make_entry('middle', tr=15000),
                    make_entry('next-nearest', tr=12000),
                ],
                when=datetime(2026, 8, 30, tzinfo=UTC),
                request_id=2,
            )
        )
        await session.commit()

    async with league_sessionmaker() as session:
        entries = await query_league_list(session, LeagueListQuery(min_tr=10000, limit=2))

    assert [entry.id for entry in entries] == ['next-nearest', 'nearest']  # noqa: S101


@pytest.mark.parametrize(
    'case',
    [
        MetricCase('league', 2.0, 40.0, 80.0, 'league-first'),
        MetricCase('pps', 3.0, 40.0, 80.0, 'metric-first'),
        MetricCase('apm', 2.0, 50.0, 80.0, 'metric-first'),
        MetricCase('adpm', 2.0, 40.0, 90.0, 'metric-first'),
        MetricCase('apl', 1.0, 30.0, 80.0, 'metric-first'),
        MetricCase('adpl', 1.0, 40.0, 60.0, 'metric-first'),
    ],
)
@pytest.mark.asyncio
async def test_league_list_sorts_by_selected_metric(
    league_sessionmaker: async_sessionmaker[AsyncSession],
    case: MetricCase,
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.rank.snapshot import (  # noqa: PLC0415
        LeagueListQuery,
        query_league_list,
    )

    async with league_sessionmaker() as session:
        session.add(
            make_snapshot(
                [
                    make_entry('league-first', tr=18000, pps=2.0, apm=40.0, vs=80.0),
                    make_entry('metric-first', tr=12000, pps=case.pps, apm=case.apm, vs=case.vs),
                ],
                when=datetime(2026, 8, 30, tzinfo=UTC),
                request_id=3,
            )
        )
        await session.commit()

    async with league_sessionmaker() as session:
        entries = await query_league_list(session, LeagueListQuery(sort=case.sort))

    assert entries[0].id == case.expected_first  # noqa: S101


@pytest.mark.asyncio
async def test_league_list_uses_visible_metric_precision_before_tr_tiebreak(
    league_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.rank.snapshot import (  # noqa: PLC0415
        LeagueListQuery,
        query_league_list,
    )

    async with league_sessionmaker() as session:
        session.add(
            make_snapshot(
                [
                    make_entry('higher-tr', tr=18000, vs=80.0),
                    make_entry('higher-raw-adpm', tr=12000, vs=80.006),
                ],
                when=datetime(2026, 8, 30, tzinfo=UTC),
                request_id=4,
            )
        )
        await session.commit()

    async with league_sessionmaker() as session:
        entries = await query_league_list(session, LeagueListQuery(sort='adpm'))

    assert [entry.id for entry in entries] == ['higher-tr', 'higher-raw-adpm']  # noqa: S101


@pytest.mark.asyncio
async def test_league_list_reads_only_the_latest_persisted_snapshot(
    league_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.rank.snapshot import (  # noqa: PLC0415
        LeagueListQuery,
        query_league_list,
    )

    async with league_sessionmaker() as session:
        session.add(
            make_snapshot(
                [make_entry('stale', tr=20000)],
                when=datetime(2026, 8, 29, tzinfo=UTC),
                request_id=5,
            )
        )
        await session.flush()
        session.add(
            make_snapshot(
                [make_entry('fresh', tr=10000)],
                when=datetime(2026, 8, 30, tzinfo=UTC),
                request_id=6,
            )
        )
        await session.commit()

    async with league_sessionmaker() as session:
        entries = await query_league_list(session, LeagueListQuery())

    assert [entry.id for entry in entries] == ['fresh']  # noqa: S101


@pytest.mark.asyncio
async def test_league_list_reports_missing_snapshot(
    league_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio.rank.snapshot import (  # noqa: PLC0415
        LeagueListQuery,
        LeagueSnapshotNotFoundError,
        query_league_list,
    )

    async with league_sessionmaker() as session:
        with pytest.raises(LeagueSnapshotNotFoundError):
            await query_league_list(session, LeagueListQuery())
