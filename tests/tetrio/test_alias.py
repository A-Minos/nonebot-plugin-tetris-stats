# ruff: noqa: S101

from asyncio import gather
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from inspect import unwrap
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from httpx import AsyncClient, MockTransport, Request, Response
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, PrivateMessageEvent
from nonebot.adapters.onebot.v11.event import Sender as EventSender
from nonebot.message import handle_event
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tarina.lang import lang  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from sqlite3 import Connection

    from nonebot.adapters import Event

    from nonebot_plugin_tetris_stats.games.tetrio.api import Player
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.leaderboards.by import BySuccessModel

    Sender = Callable[[int, str], Awaitable[str]]
    Responses = dict[str, Response]

UID = '123456789abcdef012345678'
OTHER_UID = '0123456789abcdef01234567'
MESSAGES = count(20000)


def success(username: str, uid: str) -> Response:
    return Response(
        200,
        json={
            'success': True,
            'cache': {'status': 'hit', 'cached_at': '2026-01-01T00:00:00Z', 'cached_until': '2026-01-01T00:00:00Z'},
            'data': {
                '_id': uid,
                'username': username,
                'role': 'user',
                'badges': [],
                'xp': 0,
                'gamesplayed': 0,
                'gameswon': 0,
                'gametime': 0,
                'supporter_tier': 0,
                'connections': {},
                'achievements': [],
                'ar': 0,
                'ar_counts': {},
                'oldusernames': [],
            },
        },
    )


@pytest.fixture(scope='module')
async def alias_database() -> AsyncIterator[None]:
    from nonebot_plugin_orm import Model, get_session  # noqa: PLC0415
    from nonebot_plugin_permission import system  # type: ignore[import-untyped]  # noqa: PLC0415

    async with get_session() as session:
        connection = await session.connection()
        engine = connection.engine
        await connection.run_sync(Model.metadata.create_all)
        await session.commit()
    await system.load()
    yield
    await engine.dispose()


@pytest.fixture
async def tetrio_http(monkeypatch: pytest.MonkeyPatch) -> 'AsyncIterator[Responses]':
    from nonebot_plugin_tetris_stats.games.tetrio.api import cache  # noqa: PLC0415

    responses: Responses = {}

    def respond(request: Request) -> Response:
        return responses[request.url.path]

    await cache.Cache.cache.clear()
    async with AsyncClient(transport=MockTransport(respond)) as client:
        monkeypatch.setattr(cache.request, 'client', client)
        # Keep production Request.request; skip the one-second limiter in this local transport test.
        monkeypatch.setattr(cache.request, 'request', unwrap(cache.request.request))
        yield responses
    await cache.Cache.cache.clear()


@pytest.fixture
async def command_sender(monkeypatch: pytest.MonkeyPatch, alias_database: None) -> 'AsyncIterator[Sender]':  # noqa: ARG001
    from nonebot_plugin_alconna import UniMessage  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games.tetrio import query  # noqa: PLC0415

    sent: list[str] = []
    bot = Bot(get_adapter(Adapter), '1')

    async def send(_bot: Bot, event: 'Event', message: object, **_kwargs: object) -> None:  # noqa: ARG001
        sent.append(str(message))

    async def render(player: 'Player', *_args: object) -> UniMessage:
        return UniMessage((await player.user).ID)

    async def run(user_id: int, command: str) -> str:
        sent.clear()
        message = Message(command)
        event = PrivateMessageEvent(
            time=0,
            self_id=1,
            post_type='message',
            sub_type='friend',
            message_type='private',
            font=0,
            sender=EventSender(user_id=user_id, nickname='alias-test'),
            to_me=True,
            user_id=user_id,
            message_id=next(MESSAGES),
            message=message,
            original_message=message,
            raw_message=command,
        )
        await handle_event(bot, event)
        (reply,) = sent
        return reply

    monkeypatch.setattr(Bot, 'send', send)
    monkeypatch.setattr(query, 'make_query_result', render)
    previous = lang.current
    lang.select('zh-CN')
    try:
        yield run
    finally:
        lang.select(previous)


async def allow_alias_management(user_id: int) -> None:
    from arclet.cithun import Permission  # type: ignore[import-untyped]  # noqa: PLC0415
    from nonebot_plugin_permission import system  # type: ignore[import-untyped]  # noqa: PLC0415
    from nonebot_plugin_uninfo import SupportScope  # noqa: PLC0415
    from nonebot_plugin_user import get_user  # noqa: PLC0415

    user = await get_user(SupportScope.qq_client, str(user_id))
    subject = await system.get_or_create_user(f'user:{user.id}', user.name)
    await system.assign(subject, 'tetris.TETRIO.alias.*', Permission.VISIT | Permission.AVAILABLE)


async def test_alias_command_lifecycle(command_sender: 'Sender', tetrio_http: 'Responses') -> None:
    from nonebot_plugin_orm import get_session  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games.tetrio.models import (  # noqa: PLC0415
        TETRIOPlayerAlias,
        TETRIOUserUniqueIdentifier,
    )

    async with get_session() as session:
        prior = TETRIOUserUniqueIdentifier(user_unique_identifier=UID)
        session.add(prior)
        await session.flush()
        prior_id = prior.id
        await session.commit()
    tetrio_http['/api/users/renamed'] = success('renamed', UID)
    tetrio_http['/api/users/otherplayer'] = success('otherplayer', OTHER_UID)
    tetrio_http[f'/api/users/{UID}'] = success('renamed', UID)
    tetrio_http[f'/api/users/{OTHER_UID}'] = success('otherplayer', OTHER_UID)
    tetrio_http['/api/users/dtg'] = success('dtg', OTHER_UID)
    manager, other = 20001, 20002
    denied = '你没有执行此命令的权限'

    assert await command_sender(other, 'ioalias add DTG renamed') == denied
    await allow_alias_management(manager)
    saved = '已保存 dtg。用 iostats dtg 查询该玩家。'
    assert await command_sender(manager, 'ioalias add DTG renamed') == saved
    assert await command_sender(manager, 'ioalias add dtg renamed') == saved
    assert await command_sender(manager, f'ioalias add second {UID}') == '已保存 second。用 iostats second 查询该玩家。'
    assert await command_sender(other, 'iostats DTG --template v2') == UID
    assert await command_sender(other, 'iostats ~DTG --template v2') == UID
    assert await command_sender(other, 'ioalias remove DTG') == denied
    await allow_alias_management(other)
    assert await command_sender(other, 'ioalias add dtg otherplayer') == (
        'dtg 已绑定其他玩家。要更换目标，请先删除这个别名。'  # noqa: RUF001
    )
    assert await command_sender(manager, 'iostats ~dtg --template v2') == UID
    assert await command_sender(other, 'ioalias remove DTG') == '已删除 dtg。'
    assert await command_sender(manager, 'iostats ~dtg --template v2') == '没有名为 dtg 的共用别名。'
    assert await command_sender(manager, 'iostats dtg --template v2') == OTHER_UID
    assert await command_sender(other, 'ioalias add DTG otherplayer') == saved
    assert await command_sender(manager, 'iostats ~dtg --template v2') == OTHER_UID
    assert await command_sender(other, 'iostats ~second --template v2') == UID
    assert await command_sender(other, 'ioalias remove second') == '已删除 second。'
    async with get_session() as session:
        prior = await session.get(TETRIOUserUniqueIdentifier, prior_id)
        assert prior is not None and prior.user_unique_identifier == UID
        assert await session.get(TETRIOPlayerAlias, 'second') is None


@pytest.mark.parametrize('target', [OTHER_UID, 'regular_player'])
async def test_direct_iostats_targets_need_no_alias(
    command_sender: 'Sender', tetrio_http: 'Responses', target: str
) -> None:
    tetrio_http[f'/api/users/{target}'] = success('regular_player', OTHER_UID)
    assert await command_sender(next(MESSAGES), f'iostats {target} --template v2') == OTHER_UID


@pytest.fixture
async def alias_sessions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    from nonebot_plugin_tetris_stats.games.tetrio import alias  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.models import (  # noqa: PLC0415
        TETRIOPlayerAlias,
        TETRIOUserUniqueIdentifier,
    )

    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path / "aliases.db"}')

    @event.listens_for(engine.sync_engine, 'connect')
    def enable_foreign_keys(connection: 'Connection', _record: object) -> None:
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

    try:
        async with engine.begin() as connection:
            await connection.run_sync(TETRIOUserUniqueIdentifier.__table__.create)
            await connection.run_sync(TETRIOPlayerAlias.__table__.create)
        sessions = async_sessionmaker(engine)
        monkeypatch.setattr(alias, 'get_session', sessions)
        yield sessions
    finally:
        await engine.dispose()


@pytest.mark.parametrize('other_uid', [UID, OTHER_UID])
async def test_concurrent_alias_upserts(alias_sessions: async_sessionmaker[AsyncSession], other_uid: str) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio import alias  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.models import (  # noqa: PLC0415
        TETRIOPlayerAlias,
        TETRIOUserUniqueIdentifier,
    )

    first, second = await gather(alias.save_alias('dtg', UID), alias.save_alias('dtg', other_uid))
    assert (first and second) if other_uid == UID else (first is not second)
    async with alias_sessions() as session:
        stored = await session.get(TETRIOPlayerAlias, 'dtg')
        assert stored is not None
        expected = UID if first else other_uid
        registered = (await session.scalars(select(TETRIOUserUniqueIdentifier))).one()
        assert stored.uid_id == registered.id and registered.user_unique_identifier == expected
        await session.delete(registered)
        with pytest.raises(IntegrityError):
            await session.flush()


async def test_alias_and_rank_refresh_share_uid_index(
    alias_sessions: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio import alias, rank  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.models import (  # noqa: PLC0415
        TETRIOLeagueHistorical,
        TETRIOLeagueStats,
        TETRIOLeagueStatsField,
        TETRIOLeagueUserMap,
        TETRIOPlayerAlias,
        TETRIOUserUniqueIdentifier,
    )
    from tests.tetrio.test_list import make_entry, make_snapshot  # noqa: PLC0415

    async with alias_sessions() as session:
        connection = await session.connection()
        await connection.run_sync(
            TETRIOLeagueStats.metadata.create_all,
            tables=[
                TETRIOLeagueStats.__table__,
                TETRIOLeagueHistorical.__table__,
                TETRIOLeagueStatsField.__table__,
                TETRIOLeagueUserMap.__table__,
            ],
        )
        await session.commit()

    snapshot = make_snapshot(
        [make_entry(UID, tr=12000), make_entry(OTHER_UID, tr=11000)],
        when=datetime.now(UTC),
        request_id=1,
    )

    async def leaderboard(*_args: object) -> 'BySuccessModel':
        return snapshot.raw[0].data

    monkeypatch.setattr(rank, 'by', leaderboard)
    monkeypatch.setattr(rank, 'get_session', alias_sessions)
    monkeypatch.setattr(rank, 'RANK_PERCENTILE', {'s': 100.0})
    saved, _ = await gather(alias.save_alias('dtg', UID), rank.get_tetra_league_data())
    assert saved

    async with alias_sessions() as session:
        stored = await session.get(TETRIOPlayerAlias, 'dtg')
        indexed = (await session.scalars(select(TETRIOUserUniqueIdentifier))).all()
        maps = (await session.scalars(select(TETRIOLeagueUserMap).order_by(TETRIOLeagueUserMap.entry_index))).all()
    uid_ids = {uid.user_unique_identifier: uid.id for uid in indexed}
    assert uid_ids.keys() == {UID, OTHER_UID}
    assert stored is not None and stored.uid_id == uid_ids[UID]
    assert [mapping.uid_id for mapping in maps] == [uid_ids[UID], uid_ids[OTHER_UID]]
