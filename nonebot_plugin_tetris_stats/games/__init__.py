from collections.abc import Callable

from nonebot.adapters import Bot
from nonebot.matcher import Matcher
from nonebot.message import run_postprocessor
from nonebot.typing import T_Handler
from nonebot_plugin_alconna import AlcMatches, Alconna, At, CommandMeta, on_alconna

from .. import ns
from ..i18n import Lang
from ..utils.exception import NeedCatchError
from ..utils.help_extension import HelpImageExtension
from ..utils.help_formatter import StructuredHelpFormatter

command: Alconna = Alconna(
    ['tetris-stats', 'tstats'],
    namespace=ns,
    meta=CommandMeta(
        description='俄罗斯方块相关游戏数据查询',
        fuzzy_match=True,
    ),
    formatter_type=StructuredHelpFormatter,
)
# StructuredHelpFormatter needs the root reference to resolve canonical
# subcommand metadata. Alconna instantiates formatter_type into self.formatter,
# we just back-fill the root pointer here.
command.formatter.root = command  # type: ignore[attr-defined]

alc = on_alconna(
    command=command,
    skip_for_unmatch=False,
    auto_send_output=True,
    use_origin=True,
    # WARNING: only one output_converter Extension may be attached to this
    # matcher. Future special-output customisation must be merged INTO
    # HelpImageExtension. See utils/help_extension.py docstring.
    extensions=[HelpImageExtension()],
)


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
    await matcher.send(str(exception))
