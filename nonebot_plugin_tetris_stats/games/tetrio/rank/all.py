from datetime import timedelta

from arclet.alconna import Arg
from nonebot_plugin_alconna import Option, Subcommand, UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ....db import trigger
from ....utils.host import HostPage, get_self_netloc
from ....utils.metrics import get_metrics
from ....utils.render import render
from ....utils.render.schemas.tetrio.rank.v1 import Data as DataV1
from ....utils.render.schemas.tetrio.rank.v1 import ItemData as ItemDataV1
from ....utils.render.schemas.tetrio.rank.v2 import AverageData as AverageDataV2
from ....utils.render.schemas.tetrio.rank.v2 import Data as DataV2
from ....utils.render.schemas.tetrio.rank.v2 import ItemData as ItemDataV2
from ....utils.screenshot import screenshot
from .. import alc
from ..constant import GAME_TYPE
from ..models import TETRIOLeagueStats
from ..typing import Template
from . import command

command.add(
    Subcommand(
        '--all', Option('--template', Arg('template', Template), alias=['-T'], help_text='要使用的查询模板'), dest='all'
    )
)


@alc.assign('TETRIO.rank.all')
async def _(event_session: EventSession, template: Template = 'v1'):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='rank',
        command_args=['--all'],
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
        match template:
            case 'v1':
                await UniMessage.image(raw=await make_image_v1(latest_data, compare_data)).finish()
            case 'v2':
                await UniMessage.image(raw=await make_image_v2(latest_data, compare_data)).finish()


async def make_image_v1(latest_data: TETRIOLeagueStats, compare_data: TETRIOLeagueStats) -> bytes:
    async with HostPage(
        await render(
            'v1/tetrio/rank',
            DataV1(
                items={
                    i[0].rank: ItemDataV1(
                        trending=round(i[0].tr_line - i[1].tr_line, 2),
                        require_tr=round(i[0].tr_line, 2),
                        players=i[0].player_count,
                    )
                    for i in zip(latest_data.fields, compare_data.fields, strict=True)
                },
                updated_at=latest_data.update_time,
            ),
        )
    ) as page_hash:
        return await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html')


async def make_image_v2(latest_data: TETRIOLeagueStats, compare_data: TETRIOLeagueStats) -> bytes:
    async with HostPage(
        await render(
            'v2/tetrio/rank',
            DataV2(
                items={
                    i[0].rank: ItemDataV2(
                        require_tr=round(i[0].tr_line, 2),
                        trending=round(i[0].tr_line - i[1].tr_line, 2),
                        average_data=AverageDataV2(
                            pps=(metrics := get_metrics(pps=i[0].avg_pps, apm=i[0].avg_apm, vs=i[0].avg_vs)).pps,
                            apm=metrics.apm,
                            apl=metrics.apl,
                            vs=metrics.vs,
                            adpl=metrics.adpl,
                        ),
                        players=i[0].player_count,
                    )
                    for i in zip(latest_data.fields, compare_data.fields, strict=True)
                },
                updated_at=latest_data.update_time,
            ),
        )
    ) as page_hash:
        return await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html')
