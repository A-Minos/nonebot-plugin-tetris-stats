from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from nonebot.matcher import Matcher
from nonebot_plugin_orm import get_session
from sqlalchemy import func, select

from ...utils.metrics import get_metrics
from . import alc
from .api.typing import Rank
from .model import IORank

UTC = timezone.utc


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
