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
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment, PrivateMessageEvent
from nonebot.adapters.onebot.v11.event import Sender as EventSender
from nonebot.message import handle_event
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tarina.lang import lang  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from sqlite3 import Connection

    from nonebot_plugin_tetris_stats.games.tetrio.api import Player
    from nonebot_plugin_tetris_stats.games.tetrio.api.schemas.leaderboards.by import BySuccessModel

    Sender = Callable[[int, str], Awaitable[str]]
    Dispatch = Callable[[int, str], Awaitable[list[str]]]
    Responses = dict[str, Response]

pytestmark = pytest.mark.asyncio(loop_scope='session')

UID = '123456789abcdef012345678'
OTHER_UID = '0123456789abcdef01234567'
UNRANKED_UID = 'abcdef0123456789abcdef01'
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
async def command_replies(monkeypatch: pytest.MonkeyPatch, alias_database: None) -> 'AsyncIterator[Dispatch]':  # noqa: ARG001
    from nonebot_plugin_alconna import UniMessage  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games.tetrio import query  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import blitz, sprint  # noqa: PLC0415

    sent: dict[int, list[str]] = {}
    bot = Bot(get_adapter(Adapter), '1')

    async def send(_bot: Bot, event: PrivateMessageEvent, message: object, **_kwargs: object) -> None:
        sent.setdefault(event.message_id, []).append(str(message))

    async def render(player: 'Player', *_args: object) -> UniMessage:
        return UniMessage((await player.user).ID)

    async def render_record(player: 'Player', *_args: object) -> bytes:
        return (await player.user).ID.encode()

    async def run(user_id: int, command: str) -> list[str]:
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
        return sent.pop(event.message_id)

    monkeypatch.setattr(Bot, 'send', send)
    monkeypatch.setattr(query, 'make_query_result', render)
    monkeypatch.setattr(sprint, 'make_sprint_image', render_record)
    monkeypatch.setattr(blitz, 'make_blitz_image', render_record)
    previous = lang.current
    lang.select('zh-CN')
    try:
        yield run
    finally:
        lang.select(previous)


@pytest.fixture
def command_sender(command_replies: 'Dispatch') -> 'Sender':
    async def run(user_id: int, command: str) -> str:
        replies = await command_replies(user_id, command)
        return replies[-1]

    return run


def alias_notice(alias: str) -> str:
    return f'当前正在查询别名 "{alias}"\n要查询同名的 TETR.IO 玩家，请加 ~ 前缀：~{alias}'  # noqa: RUF001


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

    tetrio_http['/api/users/renamed'] = success('renamed', UID)
    tetrio_http['/api/users/otherplayer'] = success('otherplayer', OTHER_UID)
    tetrio_http[f'/api/users/{UID}'] = success('renamed', UID)
    tetrio_http[f'/api/users/{OTHER_UID}'] = success('otherplayer', OTHER_UID)
    tetrio_http['/api/users/dtg'] = success('dtg', OTHER_UID)
    manager, other = 20001, 20002
    denied = '你没有执行此命令的权限'

    assert await command_sender(other, 'ioalias add dtg renamed') == '已保存 dtg。'
    await allow_alias_management(manager)
    saved = '已保存 dtg。'
    assert await command_sender(manager, 'io alias add dtg renamed') == saved
    assert await command_sender(manager, f'ioalias add second {UID}') == '已保存 second。'
    assert await command_sender(other, 'iostats dtg --template v2') == f'{alias_notice("dtg")}\n{UID}'
    assert await command_sender(other, 'iostats ~dtg --template v2') == OTHER_UID
    assert await command_sender(manager, 'ioalias add DTG otherplayer') == '已保存 DTG。'
    assert await command_sender(other, 'iostats DTG --template v2') == f'{alias_notice("DTG")}\n{OTHER_UID}'
    assert await command_sender(other, 'ioalias list ~未登记') == '用户名/ID不合法'
    assert set((await command_sender(manager, 'ioalias list renamed')).splitlines()) == {'dtg', 'second'}
    assert set((await command_sender(manager, 'IO ALIAS list dtg')).splitlines()) == {'dtg', 'second'}
    assert await command_sender(manager, 'ioalias list ~dtg') == 'DTG'
    assert await command_sender(manager, f'ioalias list {UNRANKED_UID}') == '该玩家没有共用别名。'
    assert await command_sender(manager, f'ioalias add {OTHER_UID} renamed') == f'已保存 {OTHER_UID}。'
    assert await command_sender(other, f'iostats {OTHER_UID} --template v2') == f'{alias_notice(OTHER_UID)}\n{UID}'
    assert await command_sender(other, f'iostats ~{OTHER_UID} --template v2') == OTHER_UID
    listed = await command_sender(manager, f'ioalias list {OTHER_UID}')
    assert set(listed.splitlines()) == {'dtg', 'second', OTHER_UID}
    assert await command_sender(manager, f'ioalias remove {OTHER_UID}') == f'已删除 {OTHER_UID}。'
    assert await command_sender(manager, 'ioalias add 我 renamed') == '已保存 我。'
    assert await command_sender(other, 'iostats 我 --template v2') == '未找到绑定信息'
    assert '我' in (await command_sender(manager, 'ioalias list 我')).splitlines()
    assert await command_sender(manager, 'ioalias remove 我') == '已删除 我。'
    assert await command_sender(other, 'ioalias remove DTG') == denied
    await allow_alias_management(other)
    assert await command_sender(other, 'ioalias add dtg otherplayer') == (
        'dtg 已绑定其他玩家。要更换目标，请先删除这个别名。'  # noqa: RUF001
    )
    assert await command_sender(manager, 'iostats dtg --template v2') == f'{alias_notice("dtg")}\n{UID}'
    assert await command_sender(other, 'io alias remove dtg') == '已删除 dtg。'
    assert await command_sender(manager, 'iostats dtg --template v2') == OTHER_UID
    assert await command_sender(manager, 'iostats DTG --template v2') == f'{alias_notice("DTG")}\n{OTHER_UID}'
    assert await command_sender(other, 'ioalias remove DTG') == '已删除 DTG。'
    assert await command_sender(other, 'ioalias add dtg otherplayer') == saved
    assert await command_sender(manager, 'iostats dtg --template v2') == f'{alias_notice("dtg")}\n{OTHER_UID}'
    assert await command_sender(other, 'iostats second --template v2') == f'{alias_notice("second")}\n{UID}'
    assert await command_sender(other, 'ioalias remove second') == '已删除 second。'
    async with get_session() as session:
        stored = await session.get(TETRIOPlayerAlias, 'dtg')
        assert stored is not None and stored.uid == OTHER_UID
        assert await session.get(TETRIOPlayerAlias, 'second') is None
        assert await session.scalar(select(TETRIOUserUniqueIdentifier.id)) is None


async def test_alias_commands_record_only_the_action(command_sender: 'Sender', tetrio_http: 'Responses') -> None:
    from nonebot_plugin_orm import get_session  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.db.models import TriggerHistoricalDataV2  # noqa: PLC0415

    async with get_session() as session:
        last_trigger_id = await session.scalar(select(func.max(TriggerHistoricalDataV2.id))) or 0

    manager = 21001
    tetrio_http['/api/users/renamed'] = success('renamed', UID)
    await allow_alias_management(manager)
    assert await command_sender(manager, 'ioalias add 统计测试 renamed') == '已保存 统计测试。'
    assert '统计测试' in (await command_sender(manager, f'ioalias list {UID}')).splitlines()
    assert await command_sender(manager, 'ioalias remove 统计测试') == '已删除 统计测试。'

    async with get_session() as session:
        triggers = await session.scalars(
            select(TriggerHistoricalDataV2)
            .where(TriggerHistoricalDataV2.id > last_trigger_id, TriggerHistoricalDataV2.command_type == 'alias')
            .order_by(TriggerHistoricalDataV2.id)
        )
        assert [(row.game_platform, row.command_args) for row in triggers] == [
            ('IO', ['add']),
            ('IO', ['list']),
            ('IO', ['remove']),
        ]


@pytest.mark.parametrize('target', [OTHER_UID, 'regular_player'])
async def test_direct_iostats_targets_need_no_alias(
    command_sender: 'Sender', tetrio_http: 'Responses', target: str
) -> None:
    tetrio_http[f'/api/users/{target}'] = success('regular_player', OTHER_UID)
    assert await command_sender(next(MESSAGES), f'iostats {target} --template v2') == OTHER_UID


async def test_iostats_alias_sends_notice_and_image_together(
    command_replies: 'Dispatch', tetrio_http: 'Responses', monkeypatch: pytest.MonkeyPatch
) -> None:
    from nonebot_plugin_alconna import UniMessage  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games.tetrio import query  # noqa: PLC0415

    async def render_image(player: 'Player', *_args: object) -> UniMessage:
        return UniMessage.image(raw=(await player.user).ID.encode())

    monkeypatch.setattr(query, 'make_query_result', render_image)
    alias = 'aliasprobe'
    user_id = next(MESSAGES)
    tetrio_http['/api/users/renamed'] = success('renamed', UID)
    tetrio_http[f'/api/users/{UID}'] = success('renamed', UID)
    tetrio_http[f'/api/users/{alias}'] = success(alias, OTHER_UID)
    tetrio_http['/api/users/plainplayer'] = success('plainplayer', OTHER_UID)

    assert await command_replies(user_id, f'ioalias add {alias} renamed') == [f'已保存 {alias}。']
    assert await command_replies(user_id, f'iostats {alias} --template v2') == [
        str(Message(alias_notice(alias)) + MessageSegment.image(UID.encode())),
    ]
    direct = [str(MessageSegment.image(OTHER_UID.encode()))]
    assert await command_replies(user_id, f'iostats ~{alias} --template v2') == direct
    assert await command_replies(user_id, 'iostats plainplayer --template v2') == direct

    from nonebot_plugin_tetris_stats.utils.exception import NeedCatchError  # noqa: PLC0415

    error_text = '模拟查询失败'

    async def fail_render(*_args: object) -> UniMessage:
        raise NeedCatchError(error_text)

    monkeypatch.setattr(query, 'make_query_result', fail_render)
    assert await command_replies(user_id, f'iostats {alias} --template v2') == [error_text]


@pytest.mark.parametrize('alias', ['gg', '阿～块', 'a_very_long_player_alias'])  # noqa: RUF001
async def test_aliases_outside_username_format(command_sender: 'Sender', tetrio_http: 'Responses', alias: str) -> None:
    manager = next(MESSAGES)
    await allow_alias_management(manager)
    tetrio_http['/api/users/renamed'] = success('renamed', UID)
    tetrio_http[f'/api/users/{UID}'] = success('renamed', UID)
    assert await command_sender(manager, f'ioalias add {alias} renamed') == f'已保存 {alias}。'
    assert await command_sender(manager, f'iostats {alias} --template v2') == f'{alias_notice(alias)}\n{UID}'
    assert await command_sender(manager, f'ioalias remove {alias}') == f'已删除 {alias}。'
    assert await command_sender(manager, f'iostats {alias} --template v2') == '用户名/ID不合法'


async def test_alias_add_rejects_tilde(command_sender: 'Sender', tetrio_http: 'Responses') -> None:
    from nonebot_plugin_orm import get_session  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games.tetrio.models import TETRIOPlayerAlias  # noqa: PLC0415

    manager = next(MESSAGES)
    await allow_alias_management(manager)
    tetrio_http['/api/users/renamed'] = success('renamed', UID)
    assert await command_sender(manager, 'ioalias add 阿~块 renamed') == '别名不能包含 ~。'
    async with get_session() as session:
        assert await session.get(TETRIOPlayerAlias, '阿~块') is None


@pytest.mark.parametrize('command', ['iorecord40l', 'iorecordblitz'])
async def test_record_queries_resolve_chinese_aliases(
    command_sender: 'Sender', tetrio_http: 'Responses', command: str
) -> None:
    manager = next(MESSAGES)
    await allow_alias_management(manager)
    tetrio_http['/api/users/renamed'] = success('renamed', UID)
    tetrio_http[f'/api/users/{UID}'] = success('renamed', UID)
    alias = f'阿块{manager}'
    assert await command_sender(manager, f'ioalias add {alias} renamed') == f'已保存 {alias}。'
    assert await command_sender(manager, f'{command} {alias}') == str(MessageSegment.image(UID.encode()))
    assert await command_sender(manager, f'{command} 不存在的玩家') == '用户名/ID不合法'


@pytest.fixture
async def alias_sessions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    from nonebot_plugin_orm import Model  # noqa: PLC0415
    from nonebot_plugin_uninfo import orm as uninfo_orm  # noqa: PLC0415

    from nonebot_plugin_tetris_stats import db  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio import alias  # noqa: PLC0415

    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path / "aliases.db"}')

    @event.listens_for(engine.sync_engine, 'connect')
    def enable_foreign_keys(connection: 'Connection', _record: object) -> None:
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Model.metadata.create_all)
        sessions = async_sessionmaker(engine)
        monkeypatch.setattr(alias, 'get_session', sessions)
        # Keep concurrent session and trigger writes off the shared in-memory SQLite connection.
        monkeypatch.setattr(uninfo_orm, 'get_session', sessions)
        monkeypatch.setattr(db, 'get_session', sessions)
        yield sessions
    finally:
        await engine.dispose()


@pytest.mark.parametrize('other_uid', [UID, OTHER_UID])
async def test_concurrent_alias_upserts(
    alias_sessions: async_sessionmaker[AsyncSession],
    command_sender: 'Sender',
    tetrio_http: 'Responses',
    other_uid: str,
) -> None:
    from nonebot_plugin_tetris_stats.db.models import TriggerHistoricalDataV2  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.models import TETRIOPlayerAlias  # noqa: PLC0415

    manager = next(MESSAGES)
    await allow_alias_management(manager)
    tetrio_http[f'/api/users/{UID}'] = success('renamed', UID)
    tetrio_http[f'/api/users/{OTHER_UID}'] = success('otherplayer', OTHER_UID)
    first, second = await gather(
        command_sender(manager, f'ioalias add dtg {UID}'),
        command_sender(manager, f'ioalias add dtg {other_uid}'),
    )
    saved = '已保存 dtg。'
    other_reply = saved if other_uid == UID else 'dtg 已绑定其他玩家。要更换目标，请先删除这个别名。'  # noqa: RUF001
    assert sorted([first, second]) == sorted([saved, other_reply])
    async with alias_sessions() as session:
        stored = (await session.scalars(select(TETRIOPlayerAlias))).one()
        expected = UID if first == saved else other_uid
        assert stored.uid == expected
        triggers = await session.scalars(select(TriggerHistoricalDataV2.command_type))
        assert list(triggers) == ['alias'] * (2 if other_uid == UID else 1)


async def test_alias_for_unranked_player_stays_out_of_rank_index(
    alias_sessions: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    command_sender: 'Sender',
    tetrio_http: 'Responses',
) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio import rank  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.models import (  # noqa: PLC0415
        TETRIOLeagueUserMap,
        TETRIOPlayerAlias,
        TETRIOUserUniqueIdentifier,
    )
    from tests.tetrio.test_list import make_entry, make_snapshot  # noqa: PLC0415

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
    manager = next(MESSAGES)
    await allow_alias_management(manager)
    tetrio_http[f'/api/users/{UNRANKED_UID}'] = success('unranked', UNRANKED_UID)
    saved, _ = await gather(
        command_sender(manager, f'ioalias add unranked {UNRANKED_UID}'), rank.get_tetra_league_data()
    )
    assert saved == '已保存 unranked。'
    assert (
        await command_sender(manager, 'iostats unranked --template v2') == f'{alias_notice("unranked")}\n{UNRANKED_UID}'
    )

    async with alias_sessions() as session:
        stored = (await session.scalars(select(TETRIOPlayerAlias))).one()
        indexed = (await session.scalars(select(TETRIOUserUniqueIdentifier))).all()
        maps = (await session.scalars(select(TETRIOLeagueUserMap).order_by(TETRIOLeagueUserMap.entry_index))).all()
    uid_ids = {uid.user_unique_identifier: uid.id for uid in indexed}
    assert uid_ids.keys() == {UID, OTHER_UID}
    assert stored.uid == UNRANKED_UID
    assert [mapping.uid_id for mapping in maps] == [uid_ids[UID], uid_ids[OTHER_UID]]
