import pytest
from nonebot.adapters.onebot.v11 import Message
from nonebug import App  # type: ignore[import-untyped]

from tests.fake_event import FakeGroupMessageEvent


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('locale', 'expected'),
    [('zh-CN', '用户名/ID不合法'), ('en-US', 'Username/ID is invalid')],
)
async def test_invalid_name(app: App, locale: str, expected: str) -> None:
    from tarina.lang import lang  # type: ignore[import-untyped]  # noqa: PLC0415

    from nonebot_plugin_tetris_stats.games import alc  # noqa: PLC0415

    original_locale = lang.current
    try:
        lang.select(locale)
        raw_message = 'tstats tetrio bind 芜湖'
        message = Message(raw_message)
        event = FakeGroupMessageEvent(message=message, original_message=message, raw_message=raw_message)
        async with app.test_matcher(alc) as ctx:
            bot = ctx.create_bot()
            ctx.receive_event(bot, event)
            ctx.should_call_send(event, expected, result=None)
    finally:
        lang.select(original_locale)
