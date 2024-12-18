from collections.abc import Callable

from nonebot.adapters import Bot
from nonebot.matcher import Matcher
from nonebot.message import run_postprocessor
from nonebot.typing import T_Handler
from nonebot_plugin_alconna import AlcMatches, Alconna, At, CommandMeta, on_alconna

from .. import ns
from ..i18n.model import Lang
from ..utils.exception import MessageFormatError, NeedCatchError

command: Alconna = Alconna(
    ['tetris-stats', 'tstats'],
    namespace=ns,
    meta=CommandMeta(
        description='俄罗斯方块相关游戏数据查询',
        fuzzy_match=True,
    ),
)

alc = on_alconna(
    command=command,
    skip_for_unmatch=False,
    auto_send_output=True,
    use_origin=True,
)


def add_block_handlers(handler: Callable[[T_Handler], T_Handler]) -> None:
    @handler
    async def _(bot: Bot, matcher: Matcher, target: At):
        if isinstance(target, At) and target.target == bot.self_id:
            await matcher.finish(Lang.interaction.wrong.query_bot())


from . import tetrio, top, tos  # noqa: F401, E402


@alc.handle()
async def _(matcher: Matcher, account: MessageFormatError):
    await matcher.finish(str(account))


@alc.handle()
async def _(matcher: Matcher, matches: AlcMatches):
    if (matches.head_matched and matches.options != {}) or matches.main_args == {}:
        await matcher.finish(
            (f'{matches.error_info!r}\n' if matches.error_info is not None else '')
            + f'输入"{matches.header_result} --help"查看帮助'
        )


@run_postprocessor
async def _(matcher: Matcher, exception: NeedCatchError):
    await matcher.send(str(exception))
