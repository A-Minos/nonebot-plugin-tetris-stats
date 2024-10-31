import pytest
from nonebot.adapters.onebot.v11 import Message
from nonebug import App  # type: ignore[import-untyped]

from tests.fake_event import FakeGroupMessageEvent


@pytest.mark.asyncio
async def test_invalid_name(app: App) -> None:
    from nonebot_plugin_tetris_stats.games import alc

    raw_message = 'tstats tetrio bind 芜湖'
    message = Message(raw_message)
    event = FakeGroupMessageEvent(message=message, original_message=message, raw_message=raw_message)
    async with app.test_matcher(alc) as ctx:
        bot = ctx.create_bot()
        ctx.receive_event(bot, event)
        ctx.should_finished(alc)
        ctx.should_call_send(event, '用户名/ID不合法', result=None)
