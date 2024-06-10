from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from hashlib import sha512
from math import floor
from statistics import mean
from zoneinfo import ZoneInfo

from aiofiles import open
from nonebot import get_driver
from nonebot.compat import model_dump
from nonebot.matcher import Matcher
from nonebot.utils import run_sync
from nonebot_plugin_apscheduler import scheduler  # type: ignore[import-untyped]
from nonebot_plugin_localstore import get_data_file  # type: ignore[import-untyped]
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from sqlalchemy import func, select
from zstandard import ZstdCompressor

from ...db import trigger
from ...utils.exception import RequestError
from ...utils.metrics import get_metrics
from ...utils.retry import retry
from . import alc
from .api.schemas.base import FailedModel
from .api.schemas.tetra_league import ValidUser
from .api.schemas.user import User
from .api.tetra_league import full_export
from .api.typing import Rank
from .constant import GAME_TYPE, RANK_PERCENTILE
from .models import IORank

UTC = timezone.utc

driver = get_driver()


@alc.assign('TETRIO.rank')
async def _(matcher: Matcher, rank: Rank, event_session: EventSession):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='rank',
        command_args=[],
    ):
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
                            func.julianday(IORank.update_time)
                            - func.julianday(latest_data.update_time - timedelta(hours=24))
                        )
                    )
                    .limit(1)
                )
            ).one()
        message = ''
        if (datetime.now(UTC) - latest_data.update_time.replace(tzinfo=UTC)) > timedelta(hours=7):
            message += 'Warning: 数据超过7小时未更新, 请联系Bot主人查看后台\n'
        message += f'{rank.upper()} 段 分数线 {latest_data.tr_line:.2f} TR, {latest_data.player_count} 名玩家\n'
        if compare_data.id != latest_data.id:
            message += f'对比 {(latest_data.update_time-compare_data.update_time).total_seconds()/3600:.2f} 小时前趋势: {f"↑{difference:.2f}" if (difference:=latest_data.tr_line-compare_data.tr_line) > 0 else f"↓{-difference:.2f}" if difference < 0 else "→"}'
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
            f'数据更新时间: {latest_data.update_time.replace(tzinfo=UTC).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")}'
        )
        await matcher.finish(message)


@scheduler.scheduled_job('cron', hour='0,6,12,18', minute=0)
@retry(exception_type=RequestError, delay=timedelta(minutes=15))
async def get_tetra_league_data() -> None:
    league, original = await full_export(with_original=True)
    if isinstance(league, FailedModel):
        msg = f'排行榜数据请求错误:\n{league.error}'
        raise RequestError(msg)

    def pps(user: ValidUser) -> float:
        return user.league.pps

    def apm(user: ValidUser) -> float:
        return user.league.apm

    def vs(user: ValidUser) -> float:
        return user.league.vs

    def _min(users: list[ValidUser], field: Callable[[ValidUser], float]) -> ValidUser:
        return min(users, key=field)

    def _max(users: list[ValidUser], field: Callable[[ValidUser], float]) -> ValidUser:
        return max(users, key=field)

    def build_extremes_data(
        users: list[ValidUser],
        field: Callable[[ValidUser], float],
        sort: Callable[[list[ValidUser], Callable[[ValidUser], float]], ValidUser],
    ) -> tuple[dict[str, str], float]:
        user = sort(users, field)
        return model_dump(User(ID=user.id, name=user.username)), field(user)

    data_hash: str | None = await run_sync((await run_sync(sha512)(original)).hexdigest)()
    async with open(get_data_file('nonebot_plugin_tetris_stats', f'{data_hash}.json.zst'), mode='wb') as file:
        await file.write(await run_sync(ZstdCompressor(level=12, threads=-1).compress)(original))

    users = [i for i in league.data.users if isinstance(i, ValidUser)]
    rank_to_users: defaultdict[Rank, list[ValidUser]] = defaultdict(list)
    for i in users:
        rank_to_users[i.league.rank].append(i)
    rank_info: list[IORank] = []
    for rank, percentile in RANK_PERCENTILE.items():
        offset = floor((percentile / 100) * len(users)) - 1
        tr_line = users[offset].league.rating
        rank_users = rank_to_users[rank]
        rank_info.append(
            IORank(
                rank=rank,
                tr_line=tr_line,
                player_count=len(rank_users),
                low_pps=(build_extremes_data(rank_users, pps, _min)),
                low_apm=(build_extremes_data(rank_users, apm, _min)),
                low_vs=(build_extremes_data(rank_users, vs, _min)),
                avg_pps=mean({i.league.pps for i in rank_users}),
                avg_apm=mean({i.league.apm for i in rank_users}),
                avg_vs=mean({i.league.vs for i in rank_users}),
                high_pps=(build_extremes_data(rank_users, pps, _max)),
                high_apm=(build_extremes_data(rank_users, apm, _max)),
                high_vs=(build_extremes_data(rank_users, vs, _max)),
                update_time=league.cache.cached_at,
                file_hash=data_hash,
            )
        )
    async with get_session() as session:
        session.add_all(rank_info)
        await session.commit()


@driver.on_startup
async def _() -> None:
    async with get_session() as session:
        latest_time = await session.scalar(select(IORank.update_time).order_by(IORank.id.desc()).limit(1))
    if latest_time is None or datetime.now(tz=UTC) - latest_time.replace(tzinfo=UTC) > timedelta(hours=6):
        await get_tetra_league_data()
