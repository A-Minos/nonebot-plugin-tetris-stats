from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from nonebot import get_driver
from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from sqlalchemy import func, select

from ....db import trigger
from ....utils.host import HostPage, get_self_netloc
from ....utils.metrics import get_metrics
from ....utils.render import render
from ....utils.render.schemas.tetrio.tetrio_rank_detail import Data, SpecialData
from ....utils.screenshot import screenshot
from .. import alc
from ..api.typing import ValidRank
from ..constant import GAME_TYPE
from ..models import IORank

UTC = timezone.utc

driver = get_driver()


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
        await UniMessage.image(raw=await make_image(latest_data, compare_data)).finish()


async def make_image(latest_data: IORank, compare_data: IORank) -> bytes:
    avg = get_metrics(pps=latest_data.avg_pps, apm=latest_data.avg_apm, vs=latest_data.avg_vs)
    low_pps = get_metrics(pps=latest_data.low_pps[1])
    low_vs = get_metrics(vs=latest_data.low_vs[1])
    max_pps = get_metrics(pps=latest_data.high_pps[1])
    max_vs = get_metrics(vs=latest_data.high_vs[1])
    async with HostPage(
        await render(
            'v2/tetrio/rank/detail',
            Data(
                name=latest_data.rank,
                trending=round(latest_data.tr_line - compare_data.tr_line, 2),
                require_tr=round(latest_data.tr_line, 2),
                players=latest_data.player_count,
                minimum_data=SpecialData(
                    apm=latest_data.low_apm[1],
                    pps=low_pps.pps,
                    lpm=low_pps.lpm,
                    vs=low_vs.vs,
                    adpm=low_vs.adpm,
                    apm_holder=latest_data.low_apm[0]['name'].upper(),
                    pps_holder=latest_data.low_pps[0]['name'].upper(),
                    vs_holder=latest_data.low_vs[0]['name'].upper(),
                ),
                average_data=SpecialData(
                    apm=avg.apm,
                    pps=avg.pps,
                    lpm=avg.lpm,
                    vs=avg.vs,
                    adpm=avg.adpm,
                    apl=avg.apl,
                    adpl=avg.adpl,
                ),
                maximum_data=SpecialData(
                    apm=latest_data.high_apm[1],
                    pps=max_pps.pps,
                    lpm=max_pps.lpm,
                    vs=max_vs.vs,
                    adpm=max_vs.adpm,
                    apm_holder=latest_data.high_apm[0]['name'].upper(),
                    pps_holder=latest_data.high_pps[0]['name'].upper(),
                    vs_holder=latest_data.high_vs[0]['name'].upper(),
                ),
                updated_at=latest_data.update_time.replace(tzinfo=UTC).astimezone(ZoneInfo('Asia/Shanghai')),
            ),
        )
    ) as page_hash:
        return await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html')


async def make_text(latest_data: IORank, compare_data: IORank) -> str:
    message = ''
    if (datetime.now(UTC) - latest_data.update_time.replace(tzinfo=UTC)) > timedelta(hours=7):
        message += 'Warning: 数据超过7小时未更新, 请联系Bot主人查看后台\n'
    message += f'{latest_data.rank.upper()} 段 分数线 {latest_data.tr_line:.2f} TR, {latest_data.player_count} 名玩家\n'
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
    return message
