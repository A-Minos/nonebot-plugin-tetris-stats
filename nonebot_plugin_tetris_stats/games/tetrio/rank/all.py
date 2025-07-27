from datetime import timedelta

from arclet.alconna import Arg
from nonebot_plugin_alconna import Option, Subcommand, UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_uninfo.orm import get_session_persist_id
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ....db import trigger
from ....utils.lang import get_lang
from ....utils.metrics import get_metrics
from ....utils.render import render_image
from ....utils.render.schemas.v1.tetrio.rank import Data as DataV1
from ....utils.render.schemas.v1.tetrio.rank import ItemData as ItemDataV1
from ....utils.render.schemas.v2.tetrio.rank import AverageData as AverageDataV2
from ....utils.render.schemas.v2.tetrio.rank import Data as DataV2
from ....utils.render.schemas.v2.tetrio.rank import ItemData as ItemDataV2
from .. import alc
from ..constant import GAME_TYPE
from ..models import TETRIOLeagueStats
from ..typedefs import Template
from . import command

command.add(
    Subcommand(
        '--all', Option('--template', Arg('template', Template), alias=['-T'], help_text='要使用的查询模板'), dest='all'
    )
)


@alc.assign('TETRIO.rank.all')
async def _(event_session: Uninfo, template: Template | None = None):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='rank',
        command_args=['--all'] + ([f'--template {template}'] if template is not None else []),
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
                or latest_data
            )

            # 查询目标时间点之后的最近记录
            after = (
                await session.scalar(
                    select(TETRIOLeagueStats)
                    .where(TETRIOLeagueStats.update_time >= target_time)  # 使用 >= 避免间隙
                    .order_by(TETRIOLeagueStats.update_time.asc())
                    .limit(1)
                    .options(selectinload(TETRIOLeagueStats.fields))
                )
                or latest_data
            )

            # 确定最接近的记录
            compare_data = (
                before
                if abs((target_time - before.update_time).total_seconds())
                < abs((target_time - after.update_time).total_seconds())
                else after
            )

        match template:
            case 'v1' | None:
                await UniMessage.image(raw=await make_image_v1(latest_data, compare_data)).finish()
            case 'v2':
                await UniMessage.image(raw=await make_image_v2(latest_data, compare_data)).finish()


async def make_image_v1(latest_data: TETRIOLeagueStats, compare_data: TETRIOLeagueStats) -> bytes:
    return await render_image(
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
            lang=get_lang(),
        ),
    )


async def make_image_v2(latest_data: TETRIOLeagueStats, compare_data: TETRIOLeagueStats) -> bytes:
    return await render_image(
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
            lang=get_lang(),
        ),
    )
