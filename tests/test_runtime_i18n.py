import json
from pathlib import Path
from string import Formatter
from typing import cast

import pytest


def _flatten_resource(value: object, prefix: tuple[str, ...] = ()) -> dict[tuple[str, ...], str]:
    data = cast('dict[str, object]', value)
    flattened: dict[tuple[str, ...], str] = {}
    for key, item in data.items():
        item_path = (*prefix, key)
        if isinstance(item, dict):
            flattened.update(_flatten_resource(item, item_path))
            continue
        assert isinstance(item, str), '.lang.json leaves must be strings'  # noqa: S101
        flattened[item_path] = item
    return flattened


def _placeholders(message: str) -> set[str]:
    return {field_name for _, field_name, _, _ in Formatter().parse(message) if field_name is not None}


def test_every_locale_matches_the_canonical_resource_contract() -> None:
    resource_dir = Path(__file__).parents[1] / 'nonebot_plugin_tetris_stats' / 'i18n'
    resources = sorted(path for path in resource_dir.glob('*.json') if not path.name.startswith('.'))
    canonical = _flatten_resource(json.loads((resource_dir / 'en-US.json').read_text()))

    for resource in resources:
        localized = _flatten_resource(json.loads(resource.read_text()))
        assert localized.keys() == canonical.keys(), resource.name  # noqa: S101
        for key, canonical_message in canonical.items():
            assert _placeholders(localized[key]) == _placeholders(canonical_message), (  # noqa: S101
                resource.name,
                '.'.join(key),
            )


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


def test_request_error_is_rendered_lazily_without_losing_detail() -> None:
    from nonebot_plugin_tetris_stats.i18n import Lang  # noqa: PLC0415
    from nonebot_plugin_tetris_stats.utils.exception import RequestError  # noqa: PLC0415

    error = RequestError(Lang.error.RequestError.request.transport, detail="ConnectError('socket reset')")

    assert error.render('zh-CN') == "请求错误\nConnectError('socket reset')"  # noqa: S101
    assert error.render('en-US') == "Request error\nConnectError('socket reset')"  # noqa: S101


@pytest.mark.parametrize(
    ('locale', 'expected'),
    [
        ('zh-CN', ('是', '否')),
        ('en-US', ('Yes', 'No')),
    ],
)
def test_unbind_choices_share_display_and_cancellation(locale: str, expected: tuple[str, str]) -> None:
    from nonebot_plugin_tetris_stats.utils.lang import get_unbind_choices  # noqa: PLC0415

    choices = get_unbind_choices(locale)

    assert tuple(choices) == expected  # noqa: S101
    assert choices.is_cancelled(None)  # noqa: S101
    assert choices.is_cancelled(expected[1])  # noqa: S101
    assert not choices.is_cancelled(expected[0])  # noqa: S101


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
