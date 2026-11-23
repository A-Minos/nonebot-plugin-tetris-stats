import asyncio
import signal
from contextlib import nullcontext
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock

import pytest
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebug import App  # type: ignore[import-untyped]
from nonebug.mixin.call_api import ApiContext  # type: ignore[import-untyped]

from .test_permission import (  # noqa: F401
    chinese_locale,
    permission_database,
    permission_user,
    query_images,
    record_images,
    send_command,
)

if TYPE_CHECKING:
    from arclet.cithun import User


@pytest.mark.parametrize(
    ('command_text', 'kind'),
    [('io查 scdhh --template v2', 'query'), ('io记录blitz scdhh', 'blitz')],
)
async def test_command_finishes_before_shutdown(
    app: App,
    permission_user: tuple[int, 'User'],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    command_text: str,
    kind: str,
) -> None:
    import nonebot_plugin_wait_a_minute as wait  # noqa: PLC0415
    from nonebot_plugin_wait_a_minute import Hook, Status  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games.tetrio import query  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tetrio.record import blitz  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.browser import BrowserManager  # noqa: PLC0415

    entered, release = asyncio.Event(), asyncio.Event()
    order = []
    original_send = ApiContext.got_call_send

    def record_send(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        receipt = original_send(*args, **kwargs)
        order.append('send')
        return receipt

    monkeypatch.setattr(ApiContext, 'got_call_send', record_send)
    log = Mock()
    monkeypatch.setattr(wait, 'logger', log)
    context = AsyncMock()
    context.close.side_effect = lambda: order.append('close')
    monkeypatch.setattr(BrowserManager, '_contexts', {'test': context})
    monkeypatch.setattr(BrowserManager, '_browser', None)

    async def render(*_args: object) -> bytes:
        entered.set()
        await release.wait()
        order.append('render')
        return b'query-image'

    target, attribute = {
        'query': (query, 'make_query_image_v2'),
        'blitz': (blitz, 'make_blitz_image'),
    }[kind]
    monkeypatch.setattr(target, attribute, render)
    monkeypatch.setattr(Hook, 'tasks', [])
    monkeypatch.setattr(Hook, 'status', Status.NOT_RUNNING_YET)
    forward = Mock(side_effect=lambda _: order.append('shutdown'))
    monkeypatch.setattr('nonebot_plugin_wait_a_minute.signal.raise_signal', forward)
    command = asyncio.create_task(
        send_command(app, permission_user[0], command_text, Message(MessageSegment.image(b'query-image')))
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        assert len(Hook.tasks) == 1  # noqa: S101
        Hook.status = Status.RUNNING
        shutdown = asyncio.create_task(Hook.check_task(signal.SIGTERM))
        await asyncio.sleep(0)
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
        command.cancel()
        await asyncio.gather(command, return_exceptions=True)


@pytest.mark.parametrize('answered', [False, True])
async def test_shutdown_cancels_only_pending_unbind_confirmations(
    monkeypatch: pytest.MonkeyPatch,
    *,
    answered: bool,
) -> None:
    from nonebot_plugin_wait_a_minute import Hook, Status

    from nonebot_plugin_tetris_stats.games import alc
    from nonebot_plugin_tetris_stats.games.top import unbind

    entered, release = asyncio.Event(), asyncio.Event()

    async def confirmation(_message: str, _options: list[str]) -> Message:
        if not answered:
            entered.set()
            await release.wait()
        return Message('是')

    async def render(_data: object) -> bytes:
        entered.set()
        await release.wait()
        return b'unbind-image'

    monkeypatch.setattr(unbind, 'suggest', confirmation)
    monkeypatch.setattr(unbind, 'trigger', lambda **_: nullcontext())
    monkeypatch.setattr(unbind, 'get_session', nullcontext)
    monkeypatch.setattr(unbind, 'get_session_persist_id', AsyncMock(return_value=1))
    monkeypatch.setattr(unbind, 'query_bind_info', AsyncMock(return_value=SimpleNamespace(game_account='test')))
    monkeypatch.setattr(
        unbind,
        'Player',
        lambda **_: SimpleNamespace(user=AsyncMock(return_value=SimpleNamespace(user_name='test'))()),
    )
    monkeypatch.setattr(unbind, 'get_avatar', AsyncMock(return_value='avatar'))
    monkeypatch.setattr(unbind, 'render_image', render)
    send = AsyncMock()
    remove = AsyncMock()
    monkeypatch.setattr(unbind.UniMessage, 'send', send)
    monkeypatch.setattr(unbind, 'remove_bind', remove)
    monkeypatch.setattr(Hook, 'status', Status.NOT_RUNNING_YET)
    monkeypatch.setattr(Hook, 'tasks', [])
    monkeypatch.setattr(Hook, 'callback', None)
    forwarded = Mock()
    monkeypatch.setattr(signal, 'raise_signal', forwarded)
    handler = next(handler.call for handler in alc.handlers if handler.call.__module__ == unbind.__name__)
    command = asyncio.create_task(
        handler(
            nb_user=Mock(),
            event_session=Mock(self_id='bot'),
            interface=Mock(get_user=AsyncMock(return_value=SimpleNamespace(nick='bot', name='bot'))),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        Hook.sig_handle(Mock())(signal.SIGTERM, None)
        assert Hook.callback is not None
        await asyncio.sleep(0)
        if answered:
            forwarded.assert_not_called()
            release.set()
        await asyncio.wait_for(command, 5)
        await asyncio.wait_for(Hook.callback, 5)
        forwarded.assert_called_once_with(signal.SIGTERM)
        if answered:
            send.assert_awaited_once()
            remove.assert_awaited_once()
        else:
            send.assert_not_awaited()
            remove.assert_not_awaited()
    finally:
        release.set()
        command.cancel()
        await asyncio.gather(command, return_exceptions=True)
