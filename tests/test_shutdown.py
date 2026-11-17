import asyncio
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock

import pytest
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebug import App  # type: ignore[import-untyped]

from .test_permission import (  # noqa: F401
    chinese_locale,
    permission_database,
    permission_user,
    send_command,
)

if TYPE_CHECKING:
    from arclet.cithun import User

    from nonebot_plugin_tetris_stats.games.tetrio.api import Player


async def test_query_finishes_before_shutdown(
    app: App,
    permission_user: tuple[int, 'User'],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import nonebot_plugin_wait_a_minute as wait  # noqa: PLC0415
    from nonebot_plugin_wait_a_minute import Hook, Status  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games.tetrio import query  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.browser import BrowserManager  # noqa: PLC0415

    entered, release = asyncio.Event(), asyncio.Event()
    order = []
    original_send = query.UniMessage.send

    async def record_send(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        receipt = await original_send(*args, **kwargs)
        order.append('send')
        return receipt

    monkeypatch.setattr(query.UniMessage, 'send', record_send)
    log = Mock()
    monkeypatch.setattr(wait, 'logger', log)
    context = AsyncMock()
    context.close.side_effect = lambda: order.append('close')
    monkeypatch.setattr(BrowserManager, '_contexts', {'test': context})
    monkeypatch.setattr(BrowserManager, '_browser', None)

    async def render_query(_player: 'Player') -> bytes:
        entered.set()
        await release.wait()
        order.append('render')
        return b'query-image'

    monkeypatch.setattr(query, 'make_query_image_v2', render_query)
    monkeypatch.setattr(Hook, 'tasks', [])
    monkeypatch.setattr(Hook, 'status', Status.NOT_RUNNING_YET)
    forward = Mock(side_effect=lambda _: order.append('shutdown'))
    monkeypatch.setattr('nonebot_plugin_wait_a_minute.signal.raise_signal', forward)
    command = asyncio.create_task(
        send_command(app, permission_user[0], 'io查 scdhh --template v2', Message(MessageSegment.image(b'query-image')))
    )
    await asyncio.wait_for(entered.wait(), 5)
    assert Hook.tasks  # noqa: S101
    Hook.status = Status.RUNNING
    shutdown = asyncio.create_task(Hook.check_task(15))
    try:
        forward.assert_not_called()
        release.set()
        await asyncio.wait_for(command, 5)
        await asyncio.wait_for(shutdown, 5)
        await BrowserManager.close_browser()
        assert order == ['render', 'send', 'shutdown', 'close']  # noqa: S101
        log.opt.assert_not_called()
        assert Hook.status == Status.FINISHED  # noqa: S101
    finally:
        release.set()
        await asyncio.gather(command, shutdown, return_exceptions=True)
