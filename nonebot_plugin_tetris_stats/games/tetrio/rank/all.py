from datetime import timedelta

from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from sqlalchemy import func, select

from ....db import trigger
from ....utils.host import HostPage, get_self_netloc
from ....utils.metrics import get_metrics
from ....utils.render import render
from ....utils.render.schemas.tetrio.tetrio_rank import AverageData, Data, ItemData
from ....utils.screenshot import screenshot
from .. import alc
from ..constant import GAME_TYPE
from ..models import IORank


@alc.assign('TETRIO.rank.all')
async def _(event_session: EventSession):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='rank',
        command_args=['--all'],
    ):
        async with get_session() as session:
            latest_update_time = (
                await session.scalars(select(IORank.update_time).order_by(IORank.id.desc()).limit(1))
            ).one()
            compare_time = (
                await session.scalars(
                    select(IORank.update_time)
                    .order_by(
                        func.abs(
                            func.julianday(IORank.update_time)
                            - func.julianday(latest_update_time - timedelta(hours=24))
                        )
                    )
                    .limit(1)
                )
            ).one()
            latest_data = (
                await session.scalars(
                    select(IORank).where(IORank.update_time == latest_update_time).order_by(IORank.tr_line.desc())
                )
            ).all()
            compare_data = (
                await session.scalars(
                    select(IORank).where(IORank.update_time == compare_time).order_by(IORank.tr_line.desc())
                )
            ).all()
        async with HostPage(
            await render(
                'v2/tetrio/rank',
                Data(
                    items={
                        i[0].rank: ItemData(
                            require_tr=round(i[0].tr_line, 2),
                            trending=round(i[0].tr_line - i[1].tr_line, 2),
                            average_data=AverageData(
                                pps=(metrics := get_metrics(pps=i[0].avg_pps, apm=i[0].avg_apm, vs=i[0].avg_vs)).pps,
                                apm=metrics.apm,
                                apl=metrics.apl,
                                vs=metrics.vs,
                                adpl=metrics.adpl,
                            ),
                            players=i[0].player_count,
                        )
                        for i in zip(latest_data, compare_data, strict=True)
                    },
                    updated_at=latest_update_time,
                ),
            )
        ) as page_hash:
            await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html')
            await UniMessage.image(raw=await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html')).finish()
