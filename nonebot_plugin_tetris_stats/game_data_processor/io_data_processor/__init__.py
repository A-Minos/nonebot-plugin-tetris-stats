from re import I

from nonebot import get_driver, on_regex
from nonebot.adapters.onebot.v11 import GROUP, Bot, MessageEvent
from nonebot.matcher import Matcher

from ...utils.database import DataBase
from ...utils.recorder import receive, recorder
from .processor import Processor

driver = get_driver()


@driver.on_startup
async def _():
    await DataBase.register_column('BIND', 'IO', 'TEXT')


IOBind = on_regex(pattern=r'^io绑定|^iobind', flags=I, permission=GROUP)
IOStats = on_regex(pattern=r'^io查|^iostats', flags=I, permission=GROUP)


@IOBind.handle()
@recorder(receive)
async def _(bot: Bot, event: MessageEvent, matcher: Matcher):
    await matcher.finish(
        await Processor.handle_bind(
            message=event.raw_message, qq_number=event.sender.user_id
        )
    )


@IOStats.handle()
async def _(event: MessageEvent, matcher: Matcher):
    if event.is_tome():
        await matcher.finish('不能查询bot的信息')
    await matcher.finish(
        await Processor.handle_query(
            message=event.raw_message, qq_number=event.sender.user_id
        )
    )
