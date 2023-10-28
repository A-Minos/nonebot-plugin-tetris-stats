from arclet.alconna import Alconna, Arg, ArgFlag, Args, CommandMeta, Option
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import GROUP
from nonebot.adapters.onebot.v11 import Bot as OB11Bot
from nonebot.adapters.onebot.v11 import MessageEvent as OB11MessageEvent
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import AlcMatches, At, on_alconna

from ...utils.exception import MessageFormatError, NeedCatchError
from ...utils.typing import Me
from ..constant import QUERY_COMMAND
from .processor import Processor, User, identify_user_info

alc = on_alconna(
    Alconna(
        '茶服',
        Option(
            QUERY_COMMAND[0],
            Args(
                Arg(
                    'target',
                    identify_user_info | Me | At,
                    notice='茶服 用户名 / TeaID | @想要查询的人 | 自己',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            alias=QUERY_COMMAND[1:],
            compact=True,
            dest='query',
            help_text='查询 茶服 游戏信息',
        ),
        meta=CommandMeta(
            description='查询 TetrisOnline查服 的信息',
            example='茶服查我',
            compact=True,
            fuzzy_match=True,
        ),
    ),
    skip_for_unmatch=False,
    auto_send_output=True,
)


@alc.assign('query')
async def _(bot: OB11Bot, event: OB11MessageEvent, matcher: Matcher, target: At | Me):
    if event.is_tome() and await GROUP(bot, event):
        await matcher.finish('不能查询bot的信息')
    if isinstance(
        (
            user := identify_user_info(
                target.target if isinstance(target, At) else event.get_user_id()
            )
        ),
        MessageFormatError,
    ):
        await matcher.finish(f'{target!r}')
    try:
        proc = Processor(
            event_id=id(event),
            user=user,
            command_args=[],
        )
    except MessageFormatError as e:
        await matcher.finish(str(e))
    try:
        await matcher.finish(await proc.handle_query())
    except NeedCatchError as e:
        await matcher.finish(str(e))


@alc.assign('query')
async def _(event: Event, matcher: Matcher, target: User):
    proc = Processor(
        event_id=id(event),
        user=target,
        command_args=[],
    )
    try:
        await matcher.finish(await proc.handle_query())
    except NeedCatchError as e:
        await matcher.finish(str(e))


@alc.assign('query')
async def _(bot: Bot, matcher: Matcher, target: At | Me):
    await matcher.finish(f'{bot.type} 适配器暂不支持绑定')


@alc.handle()
async def _(matcher: Matcher, target: MessageFormatError):
    await matcher.finish(str(target))


@alc.handle()
async def _(matcher: Matcher, matches: AlcMatches):
    if matches.head_matched:
        await matcher.finish(
            f'{matches.error_info!r}\n'
            if matches.error_info is not None
            else '' + '输入"io --help"查看帮助'
        )
