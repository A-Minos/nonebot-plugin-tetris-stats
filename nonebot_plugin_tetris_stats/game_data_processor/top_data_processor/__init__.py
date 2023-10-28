from arclet.alconna import Alconna, Arg, ArgFlag, Args, CommandMeta, Option
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import GROUP
from nonebot.adapters.onebot.v11 import Bot as OB11Bot
from nonebot.adapters.onebot.v11 import MessageEvent as OB11MessageEvent
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import AlcMatches, At, on_alconna
from nonebot_plugin_orm import get_session

from ...utils.exception import MessageFormatError, NeedCatchError
from ...utils.typing import Me
from ..constant import BIND_COMMAND, QUERY_COMMAND
from .processor import Processor, User, identify_user_info, query_bind_info

alc = on_alconna(
    Alconna(
        'top',
        Option(
            BIND_COMMAND[0],
            Args(
                Arg(
                    'target',
                    identify_user_info,
                    notice='TOP 用户名',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            alias=BIND_COMMAND[1:],
            compact=True,
            dest='bind',
            help_text='绑定 TOP 账号',
        ),
        Option(
            QUERY_COMMAND[0],
            Args(
                Arg(
                    'target',
                    identify_user_info | Me | At,
                    notice='TOP 用户名 | @想要查询的人 | 自己',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            alias=QUERY_COMMAND[1:],
            compact=True,
            dest='query',
            help_text='查询 TOP 游戏信息',
        ),
        meta=CommandMeta(
            description='查询 TetrisOnline波兰服 的信息',
            example='top绑定scdhh\ntop查我',
            compact=True,
            fuzzy_match=True,
        ),
    ),
    skip_for_unmatch=False,
    auto_send_output=True,
)


@alc.assign('bind')
async def _(event: OB11MessageEvent, matcher: Matcher, target: User):
    proc = Processor(
        event_id=id(event),
        user=target,
        command_args=[],
    )
    try:
        await matcher.finish(await proc.handle_bind(source_id=event.get_user_id()))
    except NeedCatchError as e:
        await matcher.finish(str(e))


@alc.assign('bind')
async def _(bot: Bot, matcher: Matcher, target: User):
    await matcher.finish(f'{bot.type} 适配器暂不支持绑定')


@alc.assign('query')
async def _(bot: OB11Bot, event: OB11MessageEvent, matcher: Matcher, target: At | Me):
    if event.is_tome() and await GROUP(bot, event):
        await matcher.finish('不能查询bot的信息')
    bind = await query_bind_info(
        session=get_session(),
        qq_number=(target.target if isinstance(target, At) else event.get_user_id()),
    )
    if bind is None or bind.TOP_id is None:
        await matcher.finish('未查询到绑定信息')
    message = '* 由于无法验证绑定信息, 不能保证查询到的用户为本人\n'
    proc = Processor(
        event_id=id(event),
        user=User(name=bind.TOP_id),
        command_args=[],
    )
    try:
        await matcher.finish(message + await proc.handle_query())
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
