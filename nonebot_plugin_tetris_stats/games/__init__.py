from typing import Any

from nonebot.adapters import Bot
from nonebot.exception import FinishedException
from nonebot.matcher import Matcher
from nonebot.message import run_postprocessor
from nonebot_plugin_alconna import AlcMatches, AlconnaMatcher, At

from ..utils.exception import MessageFormatError, NeedCatchError


def add_default_handlers(matcher: type[AlconnaMatcher]) -> None:
    @matcher.assign('query')
    async def _(bot: Bot, matcher: Matcher, target: At):
        if isinstance(target, At) and target.target == bot.self_id:
            await matcher.finish('不能查询bot的信息')

    @matcher.handle()
    async def _(matcher: Matcher, account: MessageFormatError):
        await matcher.finish(str(account))

    @matcher.handle()
    async def _(matcher: Matcher, matches: AlcMatches):
        if matches.head_matched and matches.options != {} or matches.main_args == {}:
            await matcher.finish(
                (f'{matches.error_info!r}\n' if matches.error_info is not None else '')
                + f'输入"{matches.header_result} --help"查看帮助'
            )

    @matcher.handle()
    def _(other: Any):  # noqa: ANN401, ARG001
        raise FinishedException


from . import tetrio, top, tos  # noqa: F401, E402


@run_postprocessor
async def _(matcher: Matcher, exception: NeedCatchError):
    await matcher.send(str(exception))
