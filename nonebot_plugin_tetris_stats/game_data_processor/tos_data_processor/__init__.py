from arclet.alconna import Alconna, AllParam, Arg, ArgFlag, Args, CommandMeta, Option
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At, on_alconna
from nonebot_plugin_orm import get_session

from ...db import query_bind_info
from ...utils.exception import NeedCatchError
from ...utils.platform import get_platform
from ...utils.typing import Me
from .. import add_default_handlers
from ..constant import BIND_COMMAND, QUERY_COMMAND
from .constant import GAME_TYPE
from .processor import Processor, User, identify_user_info

alc = on_alconna(
    Alconna(
        '茶服',
        Option(
            BIND_COMMAND[0],
            Args(
                Arg(
                    'account',
                    identify_user_info,
                    notice='茶服 用户名 / TeaID',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            alias=BIND_COMMAND[1:],
            compact=True,
            dest='bind',
            help_text='绑定 茶服 账号',
        ),
        Option(
            QUERY_COMMAND[0],
            Args(
                Arg(
                    'target',
                    At | Me,
                    notice='@想要查询的人 | 自己',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
                Arg(
                    'account',
                    identify_user_info,
                    notice='茶服 用户名 / TeaID',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
                # 如果放在一个 Union Args 里, 验证顺序不能保证, 可能出错
            ),
            alias=QUERY_COMMAND[1:],
            compact=True,
            dest='query',
            help_text='查询 茶服 游戏信息',
        ),
        Arg('other', AllParam, flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL]),
        meta=CommandMeta(
            description='查询 TetrisOnline茶服 的信息',
            example='茶服查我',
            compact=True,
            fuzzy_match=True,
        ),
    ),
    skip_for_unmatch=False,
    auto_send_output=True,
    aliases={'tos', 'TOS'},
)

try:
    from nonebot.adapters.onebot.v11 import GROUP, MessageEvent
    from nonebot.adapters.onebot.v11 import Bot as OB11Bot

    @alc.assign('bind')
    async def _(event: MessageEvent, matcher: Matcher):
        await matcher.finish('QQ 平台无需绑定')

    @alc.assign('query')
    async def _(bot: OB11Bot, event: MessageEvent, matcher: Matcher, target: At | Me):
        if event.is_tome() and await GROUP(bot, event):
            await matcher.finish('不能查询bot的信息')
        proc = Processor(
            event_id=id(event),
            user=User(teaid=target.target if isinstance(target, At) else event.get_user_id()),
            command_args=[],
        )
        try:
            await matcher.finish(await proc.handle_query())
        except NeedCatchError as e:
            await matcher.finish(str(e))
except ImportError:
    pass


@alc.assign('bind')
async def _(bot: Bot, event: Event, matcher: Matcher, account: User):
    proc = Processor(
        event_id=id(event),
        user=account,
        command_args=[],
    )
    try:
        await matcher.finish(await proc.handle_bind(platform=get_platform(bot), account=event.get_user_id()))
    except NeedCatchError as e:
        await matcher.finish(str(e))


@alc.assign('query')
async def _(bot: Bot, event: Event, matcher: Matcher, target: At | Me):
    async with get_session() as session:
        bind = await query_bind_info(
            session=session,
            chat_platform=get_platform(bot),
            chat_account=(target.target if isinstance(target, At) else event.get_user_id()),
            game_platform=GAME_TYPE,
        )
    if bind is None:
        await matcher.finish('未查询到绑定信息')
    message = '* 由于无法验证绑定信息, 不能保证查询到的用户为本人\n'
    proc = Processor(
        event_id=id(event),
        user=User(name=bind.game_account),
        command_args=[],
    )
    try:
        await matcher.finish(message + await proc.handle_query())
    except NeedCatchError as e:
        await matcher.finish(str(e))


@alc.assign('query')
async def _(event: Event, matcher: Matcher, account: User):
    proc = Processor(
        event_id=id(event),
        user=account,
        command_args=[],
    )
    try:
        await matcher.finish(await proc.handle_query())
    except NeedCatchError as e:
        await matcher.finish(str(e))


add_default_handlers(alc)
