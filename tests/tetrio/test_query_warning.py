from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from tests.fake_event import FakeGroupMessageEvent

if TYPE_CHECKING:
    from nonebot.adapters import Event
    from nonebot.matcher import Matcher
    from nonebot_plugin_uninfo.model import Session as UninfoSession


@pytest.mark.asyncio
@pytest.mark.parametrize('case', [(False, True), (True, False)])
async def test_bound_query_warns_only_for_unverified_account(
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[bool, bool],
) -> None:
    from nonebot.adapters.onebot.v11 import Message  # noqa: PLC0415
    from nonebot_plugin_alconna.uniseg import UniMessage  # noqa: PLC0415
    from nonebot_plugin_alconna.uniseg.segment import I18n  # noqa: PLC0415
    from nonebot_plugin_user.models import User  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.db.models import Bind  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games import alc  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio import query  # noqa: PLC0415

    verified, expects_warning = case
    bind = Bind(user_id=1, game_platform='IO', game_account='tester', verify=verified)
    user = User()
    user.id = 1
    sent: list[UniMessage] = []

    @asynccontextmanager
    async def fake_trigger(**_: object) -> AsyncIterator[None]:
        yield

    @asynccontextmanager
    async def fake_get_session() -> AsyncIterator[object]:
        yield object()

    async def fake_get_session_persist_id(_: object) -> int:
        return 1

    async def fake_get_user(*_: object) -> User:
        return user

    async def fake_query_bind_info(**_: object) -> Bind:
        return bind

    async def fake_resolve_compare_delta(*_: object) -> timedelta:
        return timedelta()

    async def fake_make_query_result(*_: object) -> UniMessage:
        return UniMessage('result')

    async def capture_finish(self: UniMessage, *_: object, **__: object) -> None:
        sent.append(self)

    monkeypatch.setattr(query, 'trigger', fake_trigger)
    monkeypatch.setattr(query, 'get_session', fake_get_session)
    monkeypatch.setattr(query, 'get_session_persist_id', fake_get_session_persist_id)
    monkeypatch.setattr(query, 'get_user', fake_get_user)
    monkeypatch.setattr(query, 'query_bind_info', fake_query_bind_info)
    monkeypatch.setattr(query, 'resolve_compare_delta', fake_resolve_compare_delta)
    monkeypatch.setattr(query, 'make_query_result', fake_make_query_result)
    monkeypatch.setattr(UniMessage, 'finish', capture_finish)

    bound_query_handler = next(handler.call for handler in alc.handlers if handler.call.__module__ == query.__name__)
    raw_message = 'tstats tetrio query 我'
    message = Message(raw_message)
    event = FakeGroupMessageEvent(message=message, original_message=message, raw_message=raw_message)

    await bound_query_handler(
        user=user,
        event=cast('Event', event),
        matcher=cast('Matcher', SimpleNamespace()),
        who='我',
        event_session=cast('UninfoSession', SimpleNamespace(scope='qq')),
        template='v2',
    )

    assert len(sent) == 1  # noqa: S101
    assert any(isinstance(segment, I18n) for segment in sent[0]) is expects_warning  # noqa: S101
