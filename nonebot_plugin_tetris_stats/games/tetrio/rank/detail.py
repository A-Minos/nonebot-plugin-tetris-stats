from zoneinfo import ZoneInfo

from arclet.alconna import Arg
from nonebot import get_driver
from nonebot_plugin_alconna import Subcommand, UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_uninfo.orm import get_session_persist_id

from ....db import trigger
from ....i18n import Lang
from ....utils.lang import get_lang
from ....utils.metrics import get_metrics
from ....utils.render import render_image
from ....utils.render.schemas.v2.tetrio.rank.detail import Data, SpecialData
from .. import assign
from ..api.schemas.leaderboards.by import Entry
from ..api.typedefs import ValidRank
from ..constant import GAME_TYPE
from ..mask import display_name, get_masks
from ..models import TETRIOLeagueStats
from . import command
from .snapshot import get_latest_and_compare_snapshots

driver = get_driver()

command.add(
    Subcommand(
        '--detail',
        Arg('rank', ValidRank, notice=Lang.command.tetrio.rank.detail.args.rank.notice.cast()),
        alias=['-D'],
        dest='detail',
        help_text=Lang.command.tetrio.rank.detail.description.cast(),
    )
)


@assign('TETRIO.rank.detail')
async def _(rank: ValidRank, event_session: Uninfo):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='rank',
        command_args=[f'--detail {rank}'],
    ):
        async with get_session() as session:
            latest_data, compare_data = await get_latest_and_compare_snapshots(session)
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
    # holder 只是字符串, 不经过 TETRIOPlayer 的统一屏蔽处理
    masks = await get_masks(
        {
            entry.id
            for entry in (
                latest_data.low_apm,
                latest_data.low_pps,
                latest_data.low_vs,
                latest_data.high_apm,
                latest_data.high_pps,
                latest_data.high_vs,
            )
        }
    )

    def holder(entry: Entry) -> str:
        return display_name(entry.username.upper(), masks.get(entry.id, ()))

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
                apm_holder=holder(latest_data.low_apm),
                pps_holder=holder(latest_data.low_pps),
                vs_holder=holder(latest_data.low_vs),
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
                apm_holder=holder(latest_data.high_apm),
                pps_holder=holder(latest_data.high_pps),
                vs_holder=holder(latest_data.high_vs),
            ),
            updated_at=latest.update_time.astimezone(ZoneInfo('Asia/Shanghai')),
            lang=get_lang(),
        ),
    )
