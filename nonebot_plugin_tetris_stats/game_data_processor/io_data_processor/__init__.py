from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from arclet.alconna import Alconna, AllParam, Arg, ArgFlag, Args, CommandMeta, Option
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At, on_alconna
from nonebot_plugin_orm import get_session
from sqlalchemy import func, select

from ...db import query_bind_info
from ...utils.exception import HandleNotFinishedError, NeedCatchError
from ...utils.metrics import get_metrics
from ...utils.platform import get_platform
from ...utils.typing import Me
from .. import add_default_handlers
from ..constant import BIND_COMMAND, QUERY_COMMAND
from .constant import GAME_TYPE
from .model import IORank
from .processor import Processor, User, identify_user_info
from .typing import Rank

UTC = timezone.utc

alc = on_alconna(
    Alconna(
        'io',
        Option(
            BIND_COMMAND[0],
            Args(
                Arg(
                    'account',
                    identify_user_info,
                    notice='IO 用户名 / ID',
                    flags=[ArgFlag.HIDDEN],
                )
            ),
            alias=BIND_COMMAND[1:],
            compact=True,
            dest='bind',
            help_text='绑定 IO 账号',
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
                    notice='IO 用户名 / ID',
                    flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
                ),
            ),
            alias=QUERY_COMMAND[1:],
            compact=True,
            dest='query',
            help_text='查询 IO 游戏信息',
        ),
        Option(
            'rank',
            Args(Arg('rank', Rank, notice='IO 段位')),
            alias={'Rank', 'RANK', '段位'},
            compact=True,
            dest='rank',
            help_text='查询 IO 段位信息',
        ),
        Arg('other', AllParam, flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL]),
        meta=CommandMeta(
            description='查询 TETR.IO 的信息',
            example='io绑定scdhh\nio查我\niorankx',
            compact=True,
            fuzzy_match=True,
        ),
    ),
    skip_for_unmatch=False,
    auto_send_output=True,
    aliases={'IO'},
)

alc.shortcut('fkosk', {'command': 'io查', 'args': ['我']})


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
        user=User(ID=bind.game_account),
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


@alc.assign('rank')
async def _(matcher: Matcher, rank: Rank):
    if rank == 'z':
        await matcher.finish('暂不支持查询未知段位')
    async with get_session() as session:
        latest_data = (
            await session.scalars(select(IORank).where(IORank.rank == rank).order_by(IORank.id.desc()).limit(1))
        ).one()
        compare_data = (
            await session.scalars(
                select(IORank)
                .where(IORank.rank == rank)
                .order_by(
                    func.abs(
                        func.julianday(IORank.create_time)
                        - func.julianday(latest_data.create_time - timedelta(hours=24))
                    )
                )
                .limit(1)
            )
        ).one()
    message = ''
    if (datetime.now(UTC) - latest_data.create_time.replace(tzinfo=UTC)) > timedelta(hours=7):
        message += 'Warning: 数据超过7小时未更新, 请联系Bot主人查看后台\n'
    message += f'{rank.upper()} 段 分数线 {latest_data.tr_line:.2f} TR, {latest_data.player_count} 名玩家\n'
    if compare_data.id != latest_data.id:
        message += f'对比 {(latest_data.create_time-compare_data.create_time).total_seconds()/3600:.2f} 小时前趋势: {f"↑{difference:.2f}" if (difference:=latest_data.tr_line-compare_data.tr_line) > 0 else f"↓{-difference:.2f}" if difference < 0 else "→"}'
    else:
        message += '暂无对比数据'
    avg = get_metrics(pps=latest_data.avg_pps, apm=latest_data.avg_apm, vs=latest_data.avg_vs)
    low_pps = get_metrics(pps=latest_data.low_pps[1])
    low_vs = get_metrics(vs=latest_data.low_vs[1])
    max_pps = get_metrics(pps=latest_data.high_pps[1])
    max_vs = get_metrics(vs=latest_data.high_vs[1])
    message += (
        '\n'
        '平均数据:\n'
        f"L'PM: {avg.lpm} ( {avg.pps} pps )\n"
        f'APM: {avg.apm} ( x{avg.apl} )\n'
        f'ADPM: {avg.adpm} ( x{avg.adpl} ) ( {avg.vs}vs )\n'
        '\n'
        '最低数据:\n'
        f"L'PM: {low_pps.lpm} ( {low_pps.pps} pps ) By: {latest_data.low_pps[0]['name'].upper()}\n"
        f'APM: {latest_data.low_apm[1]} By: {latest_data.low_apm[0]["name"].upper()}\n'
        f'ADPM: {low_vs.adpm} ( {low_vs.vs}vs ) By: {latest_data.low_vs[0]["name"].upper()}\n'
        '\n'
        '最高数据:\n'
        f"L'PM: {max_pps.lpm} ( {max_pps.pps} pps ) By: {latest_data.high_pps[0]['name'].upper()}\n"
        f'APM: {latest_data.high_apm[1]} By: {latest_data.high_apm[0]["name"].upper()}\n'
        f'ADPM: {max_vs.adpm} ( {max_vs.vs}vs ) By: {latest_data.high_vs[0]["name"].upper()}\n'
        '\n'
        f'数据更新时间: {latest_data.create_time.replace(tzinfo=UTC).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")}'
    )
    await matcher.finish(message)


add_default_handlers(alc)
