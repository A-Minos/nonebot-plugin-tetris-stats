from re import I

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP, Bot, MessageEvent
from nonebot.matcher import Matcher

from ...utils.exception import NeedCatchError
from ...utils.recorder import Recorder
from .processor import Processor

IOBind = on_regex(pattern=r'^io绑定|^iobind', flags=I, permission=GROUP)
IOStats = on_regex(pattern=r'^io查|^iostats', flags=I, permission=GROUP)


@IOBind.handle()
@Recorder.recorder(Recorder.receive)
async def _(bot: Bot, event: MessageEvent, matcher: Matcher):
    proc = Processor(
        message_id=event.message_id,
        message=event.raw_message,
        bot_id=bot.self_id,
        source_id=event.get_user_id(),
    )
    try:
        await matcher.finish(await proc.handle_bind())
    except NeedCatchError as e:
        await matcher.finish(str(e))


@IOStats.handle()
@Recorder.recorder(Recorder.receive)
async def _(bot: Bot, event: MessageEvent, matcher: Matcher):
    if event.is_tome():  # tome会把私聊判断为True 如果需要支持私聊则需要找其他办法
        await matcher.finish('不能查询bot的信息')
    proc = Processor(
        message_id=event.message_id,
        message=event.raw_message,
        bot_id=bot.self_id,
        source_id=event.get_user_id(),
    )
    try:
        await matcher.finish(await proc.handle_query())
    except NeedCatchError as e:
        await matcher.finish(str(e))
