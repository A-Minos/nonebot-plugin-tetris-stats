from contextlib import nullcontext
from importlib import import_module
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.mark.parametrize(
    ('locale', 'expected'),
    [
        ('zh-CN', ('用户名/ID不合法', '用户名不合法', '用户名/ID不合法', '时间格式不正确')),
        (
            'en-US',
            ('Username/ID is invalid', 'Username is invalid', 'Username/ID is invalid', 'Invalid duration format'),
        ),
    ],
)
def test_parser_errors_follow_locale(locale: str, expected: tuple[str, str, str, str]) -> None:
    from nonebot_plugin_tetris_stats.games.tetrio import get_player as get_tetrio_player  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.top import get_player as get_top_player  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games.tos import get_player as get_tos_player  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.duration import parse_duration  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.exception import MessageFormatError  # noqa: PLC0415

    errors: list[MessageFormatError] = []
    for parser in (get_tetrio_player, get_top_player, get_tos_player):
        with pytest.raises(MessageFormatError) as exc_info:
            parser('!')
        errors.append(exc_info.value)

    duration_error = parse_duration('invalid')
    assert isinstance(duration_error, MessageFormatError)  # noqa: S101
    errors.append(duration_error)

    assert tuple(error.render(locale) for error in errors) == expected  # noqa: S101


@pytest.mark.parametrize('locale', ['zh-CN', 'zh-TW', 'en-US', 'es-ES', 'ja-JP', 'ko-KR'])
@pytest.mark.parametrize(
    ('prompt_key', 'target'),
    [
        ('io_check', 'TETRIO.query'),
        ('io_bind', 'TETRIO.bind'),
        ('top_check', 'TOP.query'),
        ('top_bind', 'TOP.bind'),
        ('tos_check', 'TOS.query'),
        ('tos_bind', 'TOS.bind'),
    ],
)
def test_prompt_commands_reach_the_expected_handler(locale: str, prompt_key: str, target: str) -> None:
    from nonebot_plugin_tetris_stats.games import command  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.i18n import Lang  # noqa: PLC0415

    command_text = getattr(Lang.prompt, prompt_key)(locale).replace('{gameID}', 'testuser')
    result = command.parse(command_text)

    assert result.matched, result.error_info  # noqa: S101
    assert result.find(target)  # noqa: S101


def test_request_error_is_rendered_lazily_without_losing_detail() -> None:
    from nonebot_plugin_tetris_stats.i18n import Lang  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.exception import RequestError  # noqa: PLC0415

    error = RequestError(Lang.error.RequestError.request.transport, detail="ConnectError('socket reset')")

    assert error.render('zh-CN') == "请求错误\nConnectError('socket reset')"  # noqa: S101
    assert error.render('en-US') == "Request error\nConnectError('socket reset')"  # noqa: S101


@pytest.mark.asyncio
@pytest.mark.parametrize('game', ['tetrio', 'top', 'tos'])
@pytest.mark.parametrize(
    ('locale', 'expected'),
    [
        ('zh-CN', ('确定要解绑吗\uff1f', '是', '否')),
        ('en-US', ('Are you sure you want to unlink this account?', 'Yes', 'No')),
    ],
)
@pytest.mark.parametrize('answer', ['yes', 'no', None])
async def test_unbind_confirmation_uses_current_locale(
    monkeypatch: pytest.MonkeyPatch,
    game: str,
    locale: str,
    expected: tuple[str, str, str],
    answer: str | None,
) -> None:
    from nonebot.adapters.onebot.v11 import Message  # noqa: PLC0415
    from nonebot_plugin_user.models import User  # noqa: PLC0415
    from tarina.lang import lang  # type: ignore[import-untyped]  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.db.models import Bind  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.games import alc  # noqa: PLC0415

    module = import_module(f'nonebot_plugin_tetris_stats.games.{game}.unbind')
    user = User()
    user.id = 1
    bind = Bind(user_id=user.id, game_platform=module.GAME_TYPE, game_account='testuser', verify=True)
    response = None if answer is None else Message(expected[1 if answer == 'yes' else 2])
    suggest = AsyncMock(return_value=response)
    player = Mock(side_effect=RuntimeError('account lookup'))

    monkeypatch.setattr(module, 'trigger', lambda **_: nullcontext())
    monkeypatch.setattr(module, 'get_session', nullcontext)
    monkeypatch.setattr(module, 'get_session_persist_id', AsyncMock(return_value=1))
    monkeypatch.setattr(module, 'query_bind_info', AsyncMock(return_value=bind))
    monkeypatch.setattr(module, 'suggest', suggest)
    monkeypatch.setattr(module, 'Player', player)

    handler = next(handler.call for handler in alc.handlers if handler.call.__module__ == module.__name__)
    original_locale = lang.current
    try:
        lang.select(locale)
        if answer == 'yes':
            with pytest.raises(RuntimeError, match='account lookup'):
                await handler(nb_user=user, event_session=Mock(), interface=Mock())
            player.assert_called_once()
        else:
            await handler(nb_user=user, event_session=Mock(), interface=Mock())
            player.assert_not_called()
    finally:
        lang.select(original_locale)

    suggest.assert_awaited_once_with(expected[0], list(expected[1:]))


@pytest.mark.asyncio
async def test_screenshot_retry_reply_is_resolved_for_each_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    from nonebot_plugin_alconna.uniseg import UniMessage  # noqa: PLC0415
    from tarina.lang import lang  # type: ignore[import-untyped]  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.i18n import Lang  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.retry import retry  # noqa: PLC0415

    attempts = 0
    sent: list[str] = []

    async def capture_send(message: UniMessage) -> None:
        sent.append(message.extract_plain_text())

    monkeypatch.setattr(UniMessage, 'send', capture_send)

    @retry(max_attempts=2, exception_type=RuntimeError, reply=Lang.retry.screenshot)
    async def flaky_screenshot() -> bytes:
        nonlocal attempts
        attempts += 1
        if attempts % 2 == 1:
            raise RuntimeError
        return b'image'

    original_locale = lang.current
    try:
        lang.select('zh-CN')
        assert await flaky_screenshot() == b'image'  # noqa: S101
        lang.select('en-US')
        assert await flaky_screenshot() == b'image'  # noqa: S101
    finally:
        lang.select(original_locale)

    assert sent == ['截图失败\uff0c正在重试', 'Screenshot failed, retrying']  # noqa: S101
