# ruff: noqa: PLC0415, PLR2004, ANN401, I001

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from nonebot.exception import FinishedException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

UTC = timezone.utc


@pytest.fixture
async def utc_sessionmaker() -> AsyncIterator[tuple[async_sessionmaker[AsyncSession], dict[str, Any]]]:
    from nonebot_plugin_tetris_stats.db.models import TriggerHistoricalDataV2
    from nonebot_plugin_tetris_stats.games.tetrio.api.models import TETRIOHistoricalData
    from nonebot_plugin_tetris_stats.games.tetrio.models import (
        TETRIOLeagueHistorical,
        TETRIOLeagueStats,
        TETRIOLeagueUserMap,
        TETRIOUserUniqueIdentifier,
    )
    from nonebot_plugin_tetris_stats.games.top.api.models import TOPHistoricalData
    from nonebot_plugin_tetris_stats.games.tos.api.models import TOSHistoricalData

    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: TriggerHistoricalDataV2.metadata.create_all(
                sync_conn,
                tables=[
                    TOPHistoricalData.__table__,
                    TOSHistoricalData.__table__,
                    TETRIOHistoricalData.__table__,
                    TETRIOLeagueStats.__table__,
                    TETRIOLeagueHistorical.__table__,
                    TETRIOUserUniqueIdentifier.__table__,
                    TETRIOLeagueUserMap.__table__,
                    TriggerHistoricalDataV2.__table__,
                ],
            )
        )
    yield (
        async_sessionmaker(engine, expire_on_commit=False),
        {
            'TriggerHistoricalDataV2': TriggerHistoricalDataV2,
            'TETRIOHistoricalData': TETRIOHistoricalData,
            'TETRIOLeagueHistorical': TETRIOLeagueHistorical,
            'TETRIOLeagueStats': TETRIOLeagueStats,
            'TETRIOLeagueUserMap': TETRIOLeagueUserMap,
            'TETRIOUserUniqueIdentifier': TETRIOUserUniqueIdentifier,
            'TOPHistoricalData': TOPHistoricalData,
            'TOSHistoricalData': TOSHistoricalData,
        },
    )
    await engine.dispose()


def make_tos_user_profile(*, row_id: int, when: datetime) -> Any:
    from nonebot_plugin_tetris_stats.games.tos.api.schemas.user_profile import Data, UserProfile

    return UserProfile(
        code=200,
        success=True,
        data=[
            Data(
                idmultiplayergameresult=row_id,
                iduser='user-1',
                teaid='tea-1',
                time=120,
                clear_lines=40,
                attack=20,
                send=18,
                offset=5,
                receive=6,
                rise=0,
                dig=1,
                pieces=80,
                max_combo=3,
                pc_count=0,
                place=1,
                num_players=2,
                fumen_code='0',
                rule_set='ranked',
                garbage='none',
                idmultiplayergame=row_id,
                datetime=when,
            )
        ],
    )


def make_tos_user_info(*, rating_now: str, when: datetime) -> Any:
    from nonebot_plugin_tetris_stats.games.tos.api.schemas.user_info import Data, UserInfoSuccess, UserDataTotalItem

    base_total_item = UserDataTotalItem.model_construct(
        time_map='0',
        pieces_map='0',
        clear_lines_map='0',
        attacks_map='0',
        dig_map='0',
        send_map='0',
        rise_map='0',
        offset_map='0',
        receive_map='0',
        games_map='0',
        tetris_map='0',
        combo_map='0',
        tspin_map='0',
        b2b_map='0',
        perfect_clear_map='0',
        time_no_map='0',
        pieces_no_map='0',
        clear_lines_no_map='0',
        attacks_no_map='0',
        dig_no_map='0',
        send_no_map='0',
        rise_no_map='0',
        offset_no_map='0',
        receive_no_map='0',
        games_no_map='0',
        tetris_no_map='0',
        combo_no_map='0',
        tspin_no_map='0',
        b2b_no_map='0',
        perfect_clear_no_map='0',
    )
    return UserInfoSuccess.model_construct(
        code=200,
        success=True,
        data=Data.model_construct(
            teaid='tea-1',
            name='Tea',
            total_exp='0',
            ranking='0',
            ranked_games='0',
            rating_now=rating_now,
            rd_now='0',
            vol_now='0',
            rating_last='0',
            rd_last='0',
            vol_last='0',
            period_matches=[],
            user_data_total=[base_total_item],
            ranking_items='0',
            ranking_game_items='0',
            training_level='0',
            training_wins='0',
            pb_sprint='0',
            pb_marathon='0',
            pb_challenge='0',
            register_date=when,
            last_login_date=when,
        ),
    )


def make_tetrio_historical_data(*, cache_time: datetime) -> Any:
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base import Cache
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.summaries.league import (
        LeagueSuccessModel,
        Past,
        RatedData,
    )

    return LeagueSuccessModel.model_construct(
        success=True,
        cache=Cache(status='cached', cached_at=cache_time, cached_until=cache_time + timedelta(minutes=5)),
        data=RatedData.model_construct(
            decaying=False,
            past=Past.model_construct(first=None),
            gamesplayed=10,
            gameswon=6,
            glicko=1500.0,
            rd=50.0,
            gxe=0.5,
            tr=12345.0,
            rank='s',
            bestrank='s',
            standing=100,
            apm=40.0,
            pps=2.0,
            vs=80.0,
            standing_local=10,
            prev_rank='a',
            prev_at=12000,
            next_rank='ss',
            next_at=13000,
            percentile=0.9,
            percentile_rank='s',
        ),
    )


def make_tetrio_leaderboard_data(*, cache_time: datetime) -> Any:
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.base import ArCounts, Cache, P
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.leaderboards.by import Data, Entry, League, BySuccessModel

    return BySuccessModel.model_construct(
        success=True,
        cache=Cache(status='cached', cached_at=cache_time, cached_until=cache_time + timedelta(minutes=5)),
        data=Data.model_construct(
            entries=[
                Entry.model_construct(
                    id='alice',
                    username='alice',
                    role='user',
                    ts=None,
                    xp=0.0,
                    country=None,
                    supporter=None,
                    gamesplayed=10,
                    gameswon=6,
                    gametime=1.0,
                    ar=0,
                    ar_counts=ArCounts.model_construct(),
                    p=P(pri=1.0, sec=2.0, ter=3.0),
                    league=League.model_construct(
                        gamesplayed=10,
                        gameswon=6,
                        tr=12345.0,
                        gxe=0.5,
                        rank='s',
                        bestrank='s',
                        glicko=1500.0,
                        rd=50.0,
                        decaying=False,
                        pps=2.0,
                        apm=40.0,
                        vs=80.0,
                    ),
                )
            ]
        ),
    )


@pytest.mark.asyncio
async def test_top_compare_profile_accepts_aware_utc_query_params(
    utc_sessionmaker: tuple[async_sessionmaker[AsyncSession], dict[str, Any]],
) -> None:
    sessionmaker, models = utc_sessionmaker
    from nonebot_plugin_tetris_stats.games.top.api.schemas.user_profile import Data, UserProfile
    from nonebot_plugin_tetris_stats.games.top.query import get_compare_profile

    target_time = datetime(2026, 3, 8, 12, 0, tzinfo=UTC)
    before_profile = UserProfile(user_name='alice', today=Data(lpm=1, apm=2), total=None)
    after_profile = UserProfile(user_name='alice', today=Data(lpm=3, apm=4), total=None)

    async with sessionmaker() as session:
        session.add_all(
            [
                models['TOPHistoricalData'](
                    user_unique_identifier='alice',
                    api_type='User Profile',
                    data=before_profile,
                    update_time=target_time - timedelta(minutes=5),
                ),
                models['TOPHistoricalData'](
                    user_unique_identifier='alice',
                    api_type='User Profile',
                    data=after_profile,
                    update_time=target_time + timedelta(minutes=1),
                ),
            ]
        )
        await session.commit()

        result = await get_compare_profile(session, 'alice', target_time)

    assert result is not None  # noqa: S101
    assert result.today is not None  # noqa: S101
    assert result.today.lpm == 3  # noqa: S101


@pytest.mark.asyncio
async def test_tos_compare_profile_and_history_use_aware_utc(
    utc_sessionmaker: tuple[async_sessionmaker[AsyncSession], dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    sessionmaker, models = utc_sessionmaker
    import nonebot_plugin_tetris_stats.games.tos.query as tos_query

    target_time = datetime.now(UTC).replace(microsecond=0)
    history_time = target_time - timedelta(hours=3)
    before_profile = make_tos_user_profile(row_id=1, when=target_time - timedelta(minutes=5))
    after_profile = make_tos_user_profile(row_id=2, when=target_time + timedelta(minutes=1))
    history_data = make_tos_user_info(rating_now='1234.5', when=history_time)

    @asynccontextmanager
    async def fake_get_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    monkeypatch.setattr(tos_query, 'get_session', fake_get_session)

    async with sessionmaker() as session:
        session.add_all(
            [
                models['TOSHistoricalData'](
                    user_unique_identifier='tea-1',
                    api_type='User Profile',
                    data=before_profile,
                    update_time=target_time - timedelta(minutes=5),
                ),
                models['TOSHistoricalData'](
                    user_unique_identifier='tea-1',
                    api_type='User Profile',
                    data=after_profile,
                    update_time=target_time + timedelta(minutes=1),
                ),
                models['TOSHistoricalData'](
                    user_unique_identifier='tea-1',
                    api_type='User Info',
                    data=history_data,
                    update_time=history_time,
                ),
            ]
        )
        await session.commit()

        compare_profile = await tos_query.get_compare_profile(session, 'tea-1', target_time)

    historical = await tos_query.get_historical_data('tea-1')

    assert compare_profile is not None  # noqa: S101
    assert compare_profile.data[0].idmultiplayergameresult == 2  # noqa: S101
    assert historical  # noqa: S101
    assert historical[-1].score == 1234.5  # noqa: S101
    assert historical[-1].record_at == history_time.astimezone(ZoneInfo('Asia/Shanghai'))  # noqa: S101


@pytest.mark.asyncio
async def test_tetrio_nearest_historical_accepts_aware_utc(
    utc_sessionmaker: tuple[async_sessionmaker[AsyncSession], dict[str, Any]],
) -> None:
    sessionmaker, models = utc_sessionmaker
    from nonebot_plugin_tetris_stats.games.tetrio.query.v1 import get_nearest_historical, get_nearest_league_historical

    target_time = datetime(2026, 3, 8, 12, 0, tzinfo=UTC)
    historical_data = make_tetrio_historical_data(cache_time=target_time)
    leaderboard_data = make_tetrio_leaderboard_data(cache_time=target_time)

    async with sessionmaker() as session:
        session.add_all(
            [
                models['TETRIOHistoricalData'](
                    user_unique_identifier='alice',
                    api_type='league',
                    data=historical_data,
                    update_time=target_time - timedelta(minutes=3),
                ),
                models['TETRIOHistoricalData'](
                    user_unique_identifier='alice',
                    api_type='league',
                    data=historical_data,
                    update_time=target_time + timedelta(minutes=1),
                ),
            ]
        )
        await session.flush()

        stats = models['TETRIOLeagueStats'](raw=[], fields=[], update_time=target_time)
        session.add(stats)
        await session.flush()
        uid = models['TETRIOUserUniqueIdentifier'](user_unique_identifier='alice')
        session.add(uid)
        await session.flush()
        before_hist = models['TETRIOLeagueHistorical'](
            request_id=UUID('00000000-0000-0000-0000-000000000001'),
            data=leaderboard_data,
            update_time=target_time - timedelta(minutes=2),
            stats=stats,
        )
        after_hist = models['TETRIOLeagueHistorical'](
            request_id=UUID('00000000-0000-0000-0000-000000000002'),
            data=leaderboard_data,
            update_time=target_time + timedelta(minutes=4),
            stats=stats,
        )
        session.add_all([before_hist, after_hist])
        await session.flush()
        session.add_all(
            [
                models['TETRIOLeagueUserMap'](stats_id=stats.id, uid_id=uid.id, hist_id=before_hist.id, entry_index=0),
                models['TETRIOLeagueUserMap'](stats_id=stats.id, uid_id=uid.id, hist_id=after_hist.id, entry_index=0),
            ]
        )
        await session.commit()

        historical = await get_nearest_historical(session, 'alice', target_time)
        league_historical = await get_nearest_league_historical(session, 'alice', target_time)

    assert historical is not None  # noqa: S101
    assert historical.metrics.pps == 2.0  # noqa: S101
    assert historical.delta == timedelta(minutes=1)  # noqa: S101
    assert league_historical is not None  # noqa: S101
    assert league_historical.metrics.apm == 40.0  # noqa: S101
    assert league_historical.delta == timedelta(minutes=2)  # noqa: S101


@pytest.mark.asyncio
async def test_trigger_persists_aware_utc_datetimes(
    utc_sessionmaker: tuple[async_sessionmaker[AsyncSession], dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    sessionmaker, models = utc_sessionmaker
    import nonebot_plugin_tetris_stats.db as db_module

    @asynccontextmanager
    async def fake_get_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    monkeypatch.setattr(db_module, 'get_session', fake_get_session)

    with pytest.raises(FinishedException):
        async with db_module.trigger(1, 'TOP', 'query', ['--compare 1 day']):
            raise FinishedException

    async with sessionmaker() as session:
        row = await session.scalar(select(models['TriggerHistoricalDataV2']))

    assert row is not None  # noqa: S101
    assert row.trigger_time.tzinfo is UTC  # noqa: S101
    assert row.finish_time.tzinfo is UTC  # noqa: S101
    assert row.finish_time >= row.trigger_time  # noqa: S101
