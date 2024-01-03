from arclet.alconna import Alconna, AllParam, Arg, ArgFlag, Args, CommandMeta, Option
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At, on_alconna
from nonebot_plugin_orm import get_session

from ...db import query_bind_info
from ...utils.exception import HandleNotFinishedError, NeedCatchError
from ...utils.platform import get_platform
from ...utils.typing import Me
from .. import add_default_handlers
from ..constant import BIND_COMMAND, QUERY_COMMAND
from .constant import GAME_TYPE
from .processor import Processor, User, identify_user_info

alc = on_alconna(
    Alconna(
        'top',
        Option(
            BIND_COMMAND[0],
            Args(
                Arg(
                    'account',
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
                    At | Me,
                    notice='@想要查询的人 | 自己',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
                Arg(
                    'account',
                    identify_user_info | Me | At,
                    notice='TOP 用户名',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
            ),
            alias=QUERY_COMMAND[1:],
            compact=True,
            dest='query',
            help_text='查询 TOP 游戏信息',
        ),
        Arg('other', AllParam, flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL]),
        meta=CommandMeta(
            description='查询 TetrisOnline波兰服 的信息',
            example='top绑定scdhh\ntop查我',
            compact=True,
            fuzzy_match=True,
        ),
    ),
    skip_for_unmatch=False,
    auto_send_output=True,
    aliases={'TOP'},
)


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
        await matcher.send(str(e))
        raise HandleNotFinishedError from e


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
        await matcher.send(str(e))
        raise HandleNotFinishedError from e


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
        await matcher.send(str(e))
        raise HandleNotFinishedError from e


add_default_handlers(alc)
