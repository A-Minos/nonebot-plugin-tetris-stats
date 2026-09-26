from collections.abc import AsyncIterator, Iterator
from itertools import count
from typing import TYPE_CHECKING

import pytest
from arclet.cithun import Permission, User  # type: ignore[import-untyped]
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment, PrivateMessageEvent
from nonebot.adapters.onebot.v11.event import Sender
from nonebug import App  # type: ignore[import-untyped]
from sqlalchemy import select
from tarina.lang import lang  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from nonebot_plugin_tetris_stats.games.tetrio.api import Player

USER_IDS = count(1000)
MESSAGE_IDS = count(1000)
DENIED = '你没有执行此命令的权限'


@pytest.fixture(scope='session')
async def permission_database(after_nonebot_init: None) -> AsyncIterator[None]:  # noqa: ARG001
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
async def permission_user(permission_database: None) -> tuple[int, User]:  # noqa: ARG001
    from nonebot_plugin_permission import system  # noqa: PLC0415
    from nonebot_plugin_uninfo import SupportScope  # noqa: PLC0415
    from nonebot_plugin_user import get_user  # noqa: PLC0415

    platform_id = next(USER_IDS)
    user = await get_user(SupportScope.qq_client, str(platform_id))
    subject = await system.get_or_create_user(f'user:{user.id}', user.name)
    return platform_id, subject


@pytest.fixture(autouse=True)
def chinese_locale() -> Iterator[None]:
    previous = lang.current
    lang.select('zh-CN')
    yield
    lang.select(previous)


@pytest.fixture
def query_images(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from nonebot_plugin_tetris_stats.games.tetrio import query  # noqa: PLC0415

    calls: list[str] = []

    async def render_query(_player: 'Player') -> bytes:
        calls.append('query')
        return b'query-image'

    monkeypatch.setattr(query, 'make_query_image_v2', render_query)
    return calls


@pytest.fixture
def record_images(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from nonebot_plugin_tetris_stats.games.tetrio.record import blitz, sprint  # noqa: PLC0415

    calls: list[str] = []

    async def render_blitz(_player: 'Player') -> bytes:
        calls.append('blitz')
        return b'blitz-image'

    async def render_sprint(_player: 'Player') -> bytes:
        calls.append('sprint')
        return b'sprint-image'

    monkeypatch.setattr(blitz, 'make_blitz_image', render_blitz)
    monkeypatch.setattr(sprint, 'make_sprint_image', render_sprint)
    return calls


async def send_command(app: App, platform_id: int, command: str, expected: str | Message) -> None:
    from nonebot_plugin_tetris_stats.games import alc  # noqa: PLC0415

    message = Message(command)
    event = PrivateMessageEvent(
        time=0,
        self_id=1,
        post_type='message',
        sub_type='friend',
        user_id=platform_id,
        message_type='private',
        message_id=next(MESSAGE_IDS),
        message=message,
        original_message=message,
        raw_message=command,
        font=0,
        sender=Sender(user_id=platform_id, nickname='permission-test'),
        to_me=True,
    )
    async with app.test_matcher(alc) as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter), self_id='1')
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, result={'message_id': event.message_id})


@pytest.mark.parametrize(
    'command',
    [
        'tstats TETR.IO query scdhh --template v2',
        'tstats TETRIO query scdhh --template v2',
        'tstats tetr.io query scdhh --template v2',
        'tstats tetrio query scdhh --template v2',
        'tstats io query scdhh --template v2',
        'tetris-stats io query scdhh --template v2',
        'io查 scdhh --template v2',
    ],
)
async def test_query_aliases_obey_the_same_permission(
    app: App, permission_user: tuple[int, User], query_images: list[str], command: str
) -> None:
    from nonebot_plugin_permission import system  # noqa: PLC0415

    platform_id, subject = permission_user
    await system.assign(subject, 'tetris.TETRIO.query', Permission.NONE, deny_mask=Permission.AVAILABLE)
    await send_command(app, platform_id, command, DENIED)
    assert query_images == []  # noqa: S101

    await system.suset(subject, 'tetris.TETRIO.query', Permission.NONE, deny=True)
    await send_command(app, platform_id, command, Message(MessageSegment.image(b'query-image')))
    assert query_images == ['query']  # noqa: S101


async def test_default_permission_allows_query(
    app: App, permission_user: tuple[int, User], query_images: list[str]
) -> None:
    platform_id, _ = permission_user
    await send_command(app, platform_id, 'io查 scdhh --template v2', Message(MessageSegment.image(b'query-image')))
    assert query_images == ['query']  # noqa: S101


async def test_permission_denial_uses_selected_language(
    app: App, permission_user: tuple[int, User], query_images: list[str]
) -> None:
    from nonebot_plugin_permission import system  # noqa: PLC0415

    platform_id, subject = permission_user
    await system.assign(subject, 'tetris.TETRIO.query', Permission.NONE, deny_mask=Permission.AVAILABLE)
    lang.select('en-US')
    await send_command(
        app, platform_id, 'io查 scdhh --template v2', 'You do not have permission to execute this command.'
    )
    assert query_images == []  # noqa: S101


@pytest.mark.parametrize('command', ['tstats io record scdhh --40l', 'io记录40l scdhh'])
async def test_sprint_denial_does_not_block_blitz(
    app: App, permission_user: tuple[int, User], record_images: list[str], command: str
) -> None:
    from nonebot_plugin_permission import system  # noqa: PLC0415

    platform_id, subject = permission_user
    await system.assign(subject, 'tetris.TETRIO.record.sprint', Permission.NONE, deny_mask=Permission.AVAILABLE)
    await send_command(app, platform_id, command, DENIED)
    assert record_images == []  # noqa: S101

    await send_command(app, platform_id, 'io记录blitz scdhh', Message(MessageSegment.image(b'blitz-image')))
    assert record_images == ['blitz']  # noqa: S101

    await system.suset(subject, 'tetris.TETRIO.record.sprint', Permission.NONE, deny=True)
    await send_command(app, platform_id, command, Message(MessageSegment.image(b'sprint-image')))
    assert record_images == ['blitz', 'sprint']  # noqa: S101


@pytest.mark.parametrize(
    ('resource', 'command', 'game'),
    [
        ('tetris.TETRIO.config', 'tstats io config --default-compare 7d', 'IO'),
        ('tetris.TETRIO.config', 'io配置 --default-compare 7d', 'IO'),
        ('tetris.TOP.config', 'tstats TOP config --default-compare 7d', 'TOP'),
        ('tetris.TOP.config', 'top配置 --default-compare 7d', 'TOP'),
        ('tetris.TOS.config', 'tstats TOS config --default-compare 7d', 'TOS'),
        ('tetris.TOS.config', '茶服配置 --default-compare 7d', 'TOS'),
    ],
)
async def test_game_config_permissions_protect_persisted_settings(
    app: App, permission_user: tuple[int, User], resource: str, command: str, game: str
) -> None:
    from datetime import timedelta  # noqa: PLC0415

    from nonebot_plugin_orm import get_session  # noqa: PLC0415
    from nonebot_plugin_permission import system  # noqa: PLC0415
    from nonebot_plugin_uninfo import SupportScope  # noqa: PLC0415
    from nonebot_plugin_user import get_user  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games.tetrio.models import TETRIOUserConfig  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.top.models import TOPUserConfig  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tos.models import TOSUserConfig  # noqa: PLC0415

    models: dict[str, type[TETRIOUserConfig | TOPUserConfig | TOSUserConfig]] = {
        'IO': TETRIOUserConfig,
        'TOP': TOPUserConfig,
        'TOS': TOSUserConfig,
    }
    model = models[game]
    platform_id, subject = permission_user
    user = await get_user(SupportScope.qq_client, str(platform_id))
    await system.assign(subject, resource, Permission.NONE, deny_mask=Permission.AVAILABLE)
    await send_command(app, platform_id, command, DENIED)
    async with get_session() as session:
        assert await session.get(model, user.id) is None  # noqa: S101

    await system.suset(subject, resource, Permission.NONE, deny=True)
    await send_command(app, platform_id, command, Message('配置成功'))
    async with get_session() as session:
        compare_delta = await session.scalar(select(model.compare_delta).where(model.id == user.id))
        assert compare_delta == timedelta(days=7)  # noqa: S101


async def test_non_discord_verify_still_requires_permission(app: App, permission_user: tuple[int, User]) -> None:
    from nonebot_plugin_permission import system  # noqa: PLC0415

    platform_id, subject = permission_user
    await system.assign(subject, 'tetris.TETRIO.verify', Permission.NONE, deny_mask=Permission.AVAILABLE)
    await send_command(app, platform_id, 'io验证', DENIED)

    await system.suset(subject, 'tetris.TETRIO.verify', Permission.NONE, deny=True)
    await send_command(app, platform_id, 'io验证', Message('目前仅支持 Discord 账号验证'))


async def test_mask_commands_require_explicit_permission(app: App, permission_user: tuple[int, User]) -> None:
    from nonebot_plugin_permission import system  # noqa: PLC0415

    uid = '0123456789abcdef01234567'
    platform_id, subject = permission_user
    await send_command(app, platform_id, f'io屏蔽 {uid}', DENIED)

    await system.assign(subject, 'tetris.TETRIO.mask.*', Permission.VISIT | Permission.AVAILABLE)
    await send_command(app, platform_id, f'io屏蔽 {uid} 头像 bio', Message(f'{uid} 当前屏蔽字段: 头像, 简介'))
    await send_command(app, platform_id, 'io屏蔽列表', Message(f'{uid}: 头像, 简介'))
    await send_command(app, platform_id, f'io解屏蔽 {uid} avatar', Message(f'{uid} 当前屏蔽字段: 简介'))
    await send_command(
        app,
        platform_id,
        f'io屏蔽 {uid} 脚',
        Message('未知字段: 脚\n可用字段: name (名字), avatar (头像), banner (横幅), bio (简介), country (国旗)'),
    )
    await send_command(app, platform_id, f'io解屏蔽 {uid}', Message(f'{uid} 当前屏蔽字段: 无'))
    await send_command(app, platform_id, 'io屏蔽列表', Message('暂无被屏蔽的玩家'))
