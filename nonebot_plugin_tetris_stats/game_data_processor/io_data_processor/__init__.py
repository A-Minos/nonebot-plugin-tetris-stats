from re import I

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP, MessageEvent
from nonebot.matcher import Matcher

from .processor import Processor

IOBind = on_regex(pattern=r'^io绑定|^iobind', flags=I, permission=GROUP)
IOStats = on_regex(pattern=r'^io查|^iostats', flags=I, permission=GROUP)


@IOBind.handle()
async def _(event: MessageEvent, matcher: Matcher):
    await matcher.finish(
        await Processor.handle_bind(
            message=event.raw_message,
            qq_number=event.sender.user_id
        )
    )


@IOStats.handle()
async def _(event: MessageEvent, matcher: Matcher):
    if event.is_tome():
        await matcher.finish('不能查询bot的信息')
    await matcher.finish(
        await Processor.handle_query(
            message=event.raw_message,
            qq_number=event.sender.user_id
        )
    )
