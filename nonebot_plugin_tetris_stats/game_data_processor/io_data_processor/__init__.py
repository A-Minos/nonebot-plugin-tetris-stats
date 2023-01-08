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
    proc = Processor(
        message=event.raw_message, bot_id=bot.self_id, source_id=event.get_user_id()
    )
    await matcher.finish(await proc.handle_bind())


@IOStats.handle()
@recorder(receive)
async def _(bot: Bot, event: MessageEvent, matcher: Matcher):
    if event.is_tome():  # tome会把私聊判断为True 如果需要支持私聊则需要找其他办法
        await matcher.finish('不能查询bot的信息')
    proc = Processor(
        message=event.raw_message, bot_id=bot.self_id, source_id=event.get_user_id()
    )
    await matcher.finish(await proc.handle_query())
