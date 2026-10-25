from collections.abc import Callable

from nonebot.adapters import Bot
from nonebot.matcher import Matcher
from nonebot.message import run_postprocessor
from nonebot.typing import T_Handler
from nonebot_plugin_alconna import AlcMatches, Alconna, At, CommandMeta, on_alconna

from .. import ns
from ..i18n import Lang
from ..permission import command_permission
from ..utils.exception import NeedCatchError
from ..utils.help_extension import HelpImageExtension
from ..utils.help_formatter import StructuredHelpFormatter

command: Alconna = Alconna(
    ['tetris-stats', 'tstats'],
    namespace=ns,
    meta=CommandMeta(
        description=Lang.command.root.description.cast(),
        usage=Lang.command.root.usage.cast(),
        fuzzy_match=True,
    ),
    formatter_type=StructuredHelpFormatter,
)
# Alconna.__init__ 会对 meta.example 调用 str.replace 替换 `$` 前缀, LangItem 只能在构造后赋值。
command.meta.example = Lang.command.root.examples.cast()

alc = on_alconna(
    command=command,
    skip_for_unmatch=False,
    auto_send_output=True,
    use_origin=True,
    extensions=[HelpImageExtension()],
)


def assign(path: str, *, default_available: bool = True) -> Callable[[T_Handler], T_Handler]:
    game, command_name = path.split('.', maxsplit=1)
    return alc.assign(path, parameterless=command_permission(game, command_name, default_available=default_available))


def add_block_handlers(handler: Callable[[T_Handler], T_Handler]) -> None:
    @handler
    async def _(bot: Bot, matcher: Matcher, target: At):
        if isinstance(target, At) and target.target == bot.self_id:
            await matcher.finish(Lang.interaction.wrong.query_bot())


from . import tetrio, top, tos  # noqa: F401, E402


@alc.handle()
async def _(matcher: Matcher, matches: AlcMatches):
    if (matches.head_matched and matches.options != {}) or matches.main_args == {}:
        await matcher.finish(
            (f'{matches.error_info!r}\n' if matches.error_info is not None else '')
            + Lang.help.usage(command=matches.header_result)
        )


@run_postprocessor
async def _(matcher: Matcher, exception: NeedCatchError):
    await matcher.send(exception.render())
