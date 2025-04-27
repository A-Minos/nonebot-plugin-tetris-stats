from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from arclet.alconna import Arg
from nonebot import get_driver
from nonebot_plugin_alconna import Option, UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ....db import trigger
from ....utils.host import HostPage, get_self_netloc
from ....utils.lang import get_lang
from ....utils.metrics import get_metrics
from ....utils.render import render
from ....utils.render.schemas.v2.tetrio.rank.detail import Data, SpecialData
from ....utils.screenshot import screenshot
from .. import alc
from ..api.typedefs import ValidRank
from ..constant import GAME_TYPE
from ..models import TETRIOLeagueStats
from . import command

UTC = timezone.utc

driver = get_driver()

command.add(Option('--detail', Arg('rank', ValidRank), alias=['-D']))


@alc.assign('TETRIO.rank')
async def _(rank: ValidRank, event_session: EventSession):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='rank',
        command_args=[f'--detail {rank}'],
    ):
        async with get_session() as session:
            latest_data = (
                await session.scalars(
                    select(TETRIOLeagueStats)
                    .order_by(TETRIOLeagueStats.id.desc())
                    .limit(1)
                    .options(selectinload(TETRIOLeagueStats.fields))
                )
            ).one()
            compare_data = (
                await session.scalars(
                    select(TETRIOLeagueStats)
                    .order_by(
                        func.abs(
                            func.julianday(TETRIOLeagueStats.update_time)
                            - func.julianday(latest_data.update_time - timedelta(hours=24))
                        )
                    )
                    .limit(1)
                    .options(selectinload(TETRIOLeagueStats.fields))
                )
            ).one()
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
    async with HostPage(
        await render(
            'v2/tetrio/rank/detail',
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
    ) as page_hash:
        return await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html')
