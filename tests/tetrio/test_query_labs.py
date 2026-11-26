# ruff: noqa: S101

from datetime import UTC, datetime, timedelta
from inspect import unwrap
from itertools import count
from typing import TYPE_CHECKING, NamedTuple

import pytest
from httpx import AsyncClient, MockTransport, Request, Response
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment, PrivateMessageEvent
from nonebot.adapters.onebot.v11.event import Sender
from nonebot.message import handle_event
from tarina.lang import lang  # type: ignore[import-untyped]

from tests.tetrio.test_alias import UID, success
from tests.tetrio.test_alias import alias_database as query_database  # noqa: F401

if TYPE_CHECKING:
    from nonebot_plugin_tetris_stats.utils.render.schemas.v2.tetrio.user.info import Info

pytestmark = pytest.mark.asyncio(loop_scope='session')
MESSAGES = count(24000)
ACCOUNT = 'history-test'
IMAGE = b'tetris-stats-image'
PLAYER_TR = 12345
INELIGIBLE = {'success': False, 'error': {'msg': 'This user is not eligible for TETR.IO Labs.'}}


class Case(NamedTuple):
    command: str
    restricted_endpoint: str
    status: int
    body: dict[str, object]
    expected_image: bool


@pytest.mark.usefixtures('query_database')
@pytest.mark.parametrize(
    'case',
    [
        Case('iostats history-test', 'labs', 403, INELIGIBLE, expected_image=True),
        Case('iostats history-test --template v2', 'labs', 403, INELIGIBLE, expected_image=True),
        Case(
            'iostats history-test --template v2',
            'labs',
            403,
            {'success': False, 'error': {'msg': 'Forbidden'}},
            expected_image=False,
        ),
        Case('iostats history-test --template v2', 'labs', 503, INELIGIBLE, expected_image=False),
        Case('iostats history-test --template v2', 'league', 403, INELIGIBLE, expected_image=False),
    ],
)
async def test_iostats_labs_ineligibility(monkeypatch: pytest.MonkeyPatch, case: Case) -> None:  # noqa: PLR0915
    from nonebot_plugin_tetris_stats.games.tetrio.api import cache, player  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.query import make_query_result, v2  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.exception import RequestError  # noqa: PLC0415

    league = {
        'gamesplayed': 50,
        'gameswon': 30,
        'tr': PLAYER_TR,
        'glicko': 1500,
        'rd': 50,
        'gxe': 50,
        'rank': 'a',
        'bestrank': 'a',
        'standing': 999,
        'standing_local': 99,
        'apm': 45,
        'pps': 2,
        'vs': 90,
        'prev_at': 100,
        'next_at': 90,
        'percentile': 0.5,
        'percentile_rank': 'a',
        'decaying': False,
        'past': {},
    }
    solo = {'record': None, 'rank': -1, 'rank_local': -1}
    tower = {**solo, 'best': {'record': None, 'rank': -1}}
    summaries = {
        'league': league,
        '40l': solo,
        'blitz': solo,
        'zen': {'level': 2, 'score': 123},
        'zenith': tower,
        'zenithex': tower,
        'achievements': [],
    }
    lab_requests = 0

    def respond(request: Request) -> Response:
        nonlocal lab_requests
        path = request.url.path
        if path.startswith('/api/labs/leagueflow/'):
            lab_requests += 1
            if case.restricted_endpoint == 'labs':
                return Response(case.status, json=case.body)
            data: object = {'startTime': 9007199254740991, 'points': []}
        elif '/summaries/' in path:
            mode = path.rsplit('/', 1)[-1]
            if mode == case.restricted_endpoint:
                return Response(case.status, json=case.body)
            data = summaries[mode]
        else:
            return success(ACCOUNT, UID)
        today = datetime.now(UTC).isoformat()
        return Response(
            200,
            json={
                'success': True,
                'cache': {'status': 'hit', 'cached_at': today, 'cached_until': today},
                'data': data,
            },
        )

    sent: list[str] = []
    rendered: list[Info] = []

    async def capture_send(_bot: Bot, _event: PrivateMessageEvent, message: object, **_kwargs: object) -> None:
        sent.append(str(message))

    async def capture_render(info: 'Info') -> bytes:
        rendered.append(info)
        return IMAGE

    async def skip_history_write(*_args: object) -> None:
        pass

    monkeypatch.setattr(player, 'anti_duplicate_add', skip_history_write)
    monkeypatch.setattr(Bot, 'send', capture_send)
    monkeypatch.setattr(v2, 'render_image', capture_render)
    monkeypatch.setattr(v2, 'get_self_netloc', lambda: '127.0.0.1')
    bot = Bot(get_adapter(Adapter), '1')
    message = Message(case.command)
    event = PrivateMessageEvent(
        time=0,
        self_id=1,
        post_type='message',
        sub_type='friend',
        message_type='private',
        font=0,
        sender=Sender(user_id=5724, nickname=ACCOUNT),
        to_me=True,
        user_id=5724,
        message_id=next(MESSAGES),
        message=message,
        original_message=message,
        raw_message=case.command,
    )
    await cache.Cache.cache.clear()
    previous = lang.current
    lang.select('zh-CN')
    try:
        async with AsyncClient(transport=MockTransport(respond)) as client:
            monkeypatch.setattr(cache.request, 'client', client)
            monkeypatch.setattr(cache.request, 'request', unwrap(cache.request.request))
            if case.expected_image:
                await handle_event(bot, event)
            else:
                with pytest.raises(RequestError) as exc:
                    await make_query_result(player.Player(user_name=ACCOUNT), 'v2', timedelta())
                assert exc.value.status_code == case.status
                assert not rendered
                assert not sent
                return
    finally:
        lang.select(previous)
        await cache.Cache.cache.clear()

    (reply,) = sent
    (info,) = rendered
    assert info.user.name == ACCOUNT.upper()
    assert info.tetra_league is not None
    assert info.tetra_league.tr == PLAYER_TR
    assert info.tetra_league.history is None
    assert reply == str(MessageSegment.image(IMAGE))
    assert lab_requests == 1
