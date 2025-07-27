from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from arclet.alconna import Arg
from nonebot import get_driver
from nonebot_plugin_alconna import Option, UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_uninfo.orm import get_session_persist_id
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ....db import trigger
from ....utils.lang import get_lang
from ....utils.metrics import get_metrics
from ....utils.render import render_image
from ....utils.render.schemas.v2.tetrio.rank.detail import Data, SpecialData
from .. import alc
from ..api.typedefs import ValidRank
from ..constant import GAME_TYPE
from ..models import TETRIOLeagueStats
from . import command

UTC = timezone.utc

driver = get_driver()

command.add(Option('--detail', Arg('rank', ValidRank), alias=['-D']))


@alc.assign('TETRIO.rank')
async def _(rank: ValidRank, event_session: Uninfo):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='rank',
        command_args=[f'--detail {rank}'],
    ):
        async with get_session() as session:
            # 获取最新记录
            latest_data = (
                await session.scalars(
                    select(TETRIOLeagueStats)
                    .order_by(TETRIOLeagueStats.id.desc())
                    .limit(1)
                    .options(selectinload(TETRIOLeagueStats.fields))
                )
            ).one()

            # 计算目标时间点 (24小时前)
            target_time = latest_data.update_time - timedelta(hours=24)

            # 查询目标时间点之前的最近记录
            before = (
                await session.scalar(
                    select(TETRIOLeagueStats)
                    .where(TETRIOLeagueStats.update_time <= target_time)
                    .order_by(TETRIOLeagueStats.update_time.desc())
                    .limit(1)
                    .options(selectinload(TETRIOLeagueStats.fields))
                )
                or latest_data  # 回退到最新记录
            )

            # 查询目标时间点之后的最近记录
            after = (
                await session.scalar(
                    select(TETRIOLeagueStats)
                    .where(TETRIOLeagueStats.update_time >= target_time)
                    .order_by(TETRIOLeagueStats.update_time.asc())
                    .limit(1)
                    .options(selectinload(TETRIOLeagueStats.fields))
                )
                or latest_data  # 回退到最新记录
            )

            # 确定最接近的记录
            compare_data = (
                before
                if abs((target_time - before.update_time).total_seconds())
                < abs((target_time - after.update_time).total_seconds())
                else after
            )
        await UniMessage.image(
            raw=await make_image(
                rank,
                latest_data,
                compare_data,
            )
        ).finish()


async def make_image(rank: ValidRank, latest: TETRIOLeagueStats, compare: TETRIOLeagueStats) -> bytes:
    latest_data = next(filter(lambda x: x.rank == rank, latest.fields))
    compare_data = next(filter(lambda x: x.rank == rank, compare.fields))
    avg = get_metrics(pps=latest_data.avg_pps, apm=latest_data.avg_apm, vs=latest_data.avg_vs)
    low_pps = get_metrics(
        pps=latest_data.low_pps.league.pps, apm=latest_data.low_pps.league.apm, vs=latest_data.low_pps.league.vs
    )
    low_apm = get_metrics(
        pps=latest_data.low_apm.league.pps, apm=latest_data.low_apm.league.apm, vs=latest_data.low_apm.league.vs
    )
    low_vs = get_metrics(
        pps=latest_data.low_vs.league.pps, apm=latest_data.low_vs.league.apm, vs=latest_data.low_vs.league.vs
    )
    max_pps = get_metrics(
        pps=latest_data.high_pps.league.pps, apm=latest_data.high_pps.league.apm, vs=latest_data.high_pps.league.vs
    )
    max_apm = get_metrics(
        pps=latest_data.high_apm.league.pps, apm=latest_data.high_apm.league.apm, vs=latest_data.high_apm.league.vs
    )
    max_vs = get_metrics(
        pps=latest_data.high_vs.league.pps, apm=latest_data.high_vs.league.apm, vs=latest_data.high_vs.league.vs
    )
    return await render_image(
        Data(
            name=latest_data.rank,
            trending=round(latest_data.tr_line - compare_data.tr_line, 2),
            require_tr=round(latest_data.tr_line, 2),
            players=latest_data.player_count,
            minimum_data=SpecialData(
                apm=low_apm.apm,
                pps=low_pps.pps,
                lpm=low_pps.lpm,
                vs=low_vs.vs,
                adpm=low_vs.adpm,
                apm_holder=latest_data.low_apm.username.upper(),
                pps_holder=latest_data.low_pps.username.upper(),
                vs_holder=latest_data.low_vs.username.upper(),
            ),
            average_data=SpecialData(
                apm=avg.apm, pps=avg.pps, lpm=avg.lpm, vs=avg.vs, adpm=avg.adpm, apl=avg.apl, adpl=avg.adpl
            ),
            maximum_data=SpecialData(
                apm=max_apm.apm,
                pps=max_pps.pps,
                lpm=max_pps.lpm,
                vs=max_vs.vs,
                adpm=max_vs.adpm,
                apm_holder=latest_data.high_apm.username.upper(),
                pps_holder=latest_data.high_pps.username.upper(),
                vs_holder=latest_data.high_vs.username.upper(),
            ),
            updated_at=latest.update_time.replace(tzinfo=UTC).astimezone(ZoneInfo('Asia/Shanghai')),
            lang=get_lang(),
        ),
    )
