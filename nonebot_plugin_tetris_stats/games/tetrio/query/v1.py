from asyncio import gather
from datetime import timedelta
from hashlib import md5
from typing import NamedTuple

from nonebot_plugin_orm import get_session
from sqlalchemy import func, select
from yarl import URL

from ....utils.chart import get_split, get_value_bounds, handle_history_data
from ....utils.exception import FallbackError
from ....utils.host import HostPage, get_self_netloc
from ....utils.lang import get_lang
from ....utils.metrics import get_metrics
from ....utils.render import render
from ....utils.render.schemas.base import Avatar, Trending
from ....utils.render.schemas.v1.base import History
from ....utils.render.schemas.v1.tetrio.user.info import Info, Multiplayer, Singleplayer, User
from ....utils.screenshot import screenshot
from ..api import Player
from ..api.models import TETRIOHistoricalData
from ..api.schemas.summaries.league import LeagueSuccessModel, NeverRatedData, RatedData
from ..constant import TR_MAX, TR_MIN
from .tools import flow_to_history, get_league_data


def compare_trending(old: float, new: float) -> Trending:
    if old > new:
        return Trending.DOWN
    if old < new:
        return Trending.UP
    return Trending.KEEP


class Trends(NamedTuple):
    pps: Trending = Trending.KEEP
    apm: Trending = Trending.KEEP
    vs: Trending = Trending.KEEP


async def get_trending(player: Player) -> Trends:
    league = await player.league
    if not isinstance(league.data, RatedData | NeverRatedData):
        return Trends()

    async with get_session() as session:
        # 查询约一天前的历史数据
        historical = (
            await session.scalars(
                select(TETRIOHistoricalData)
                .where(
                    TETRIOHistoricalData.user_unique_identifier == (await player.user).unique_identifier,
                    TETRIOHistoricalData.api_type == 'league',
                    TETRIOHistoricalData.update_time > league.cache.cached_at - timedelta(days=1),
                )
                .order_by(
                    func.julianday(TETRIOHistoricalData.update_time)
                    - func.julianday(league.cache.cached_at - timedelta(days=1))
                )
                .limit(1)
            )
        ).one_or_none()
    if (
        historical is None
        or not isinstance(historical.data, LeagueSuccessModel)
        or not isinstance(historical.data.data, RatedData | NeverRatedData)
    ):
        return Trends()

    return Trends(
        pps=compare_trending(historical.data.data.pps, league.data.pps),
        apm=compare_trending(historical.data.data.apm, league.data.apm),
        vs=compare_trending(historical.data.data.vs, league.data.vs),
    )


async def make_query_image_v1(player: Player) -> bytes:
    (
        (user, user_info, league, sprint, blitz, leagueflow),
        (avatar_revision,),
    ) = await gather(
        gather(player.user, player.get_info(), player.league, player.sprint, player.blitz, player.get_leagueflow()),
        gather(player.avatar_revision),
    )
    league_data = get_league_data(league, RatedData)
    if league_data.vs is None:
        raise FallbackError
    histories = flow_to_history(leagueflow, handle_history_data)
    values = get_value_bounds([i.score for i in histories])
    split_value, offset = get_split(values, TR_MAX, TR_MIN)
    if sprint.data.record is not None:
        duration = timedelta(milliseconds=sprint.data.record.results.stats.finaltime).total_seconds()
        sprint_value = f'{duration:.3f}s' if duration < 60 else f'{duration // 60:.0f}m {duration % 60:.3f}s'  # noqa: PLR2004
    else:
        sprint_value = 'N/A'
    blitz_value = f'{blitz.data.record.results.stats.score:,}' if blitz.data.record is not None else 'N/A'
    netloc = get_self_netloc()
    dsps: float
    dspp: float
    # make mypy happy
    async with HostPage(
        page=await render(
            'v1/tetrio/info',
            Info(
                user=User(
                    avatar=str(
                        URL(f'http://{netloc}/host/resource/tetrio/avatars/{user.ID}') % {'revision': avatar_revision}
                    )
                    if avatar_revision is not None and avatar_revision != 0
                    else Avatar(
                        type='identicon',
                        hash=md5(user.ID.encode()).hexdigest(),  # noqa: S324
                    ),
                    name=user.name.upper(),
                    bio=user_info.data.bio,
                ),
                multiplayer=Multiplayer(
                    glicko=f'{round(league_data.glicko, 2):,}',
                    rd=round(league_data.rd, 2),
                    rank=league_data.rank,
                    tr=f'{round(league_data.tr, 2):,}',
                    global_rank=league_data.standing,
                    history=History(
                        data=histories,
                        split_interval=split_value,
                        min_value=values.value_min,
                        max_value=values.value_max,
                        offset=offset,
                    ),
                    lpm=(metrics := get_metrics(pps=league_data.pps, apm=league_data.apm, vs=league_data.vs)).lpm,
                    pps=metrics.pps,
                    lpm_trending=(trends := (await get_trending(player))).pps,
                    apm=metrics.apm,
                    apl=metrics.apl,
                    apm_trending=trends.apm,
                    adpm=metrics.adpm,
                    vs=metrics.vs,
                    adpl=metrics.adpl,
                    adpm_trending=trends.vs,
                    app=(app := (league_data.apm / (60 * league_data.pps))),
                    dsps=(dsps := ((league_data.vs / 100) - (league_data.apm / 60))),
                    dspp=(dspp := (dsps / league_data.pps)),
                    ci=150 * dspp - 125 * app + 50 * (league_data.vs / league_data.apm) - 25,
                    ge=2 * ((app * dsps) / league_data.pps),
                ),
                singleplayer=Singleplayer(
                    sprint=sprint_value,
                    blitz=blitz_value,
                ),
                lang=get_lang(),
            ),
        )
    ) as page_hash:
        return await screenshot(f'http://{netloc}/host/{page_hash}.html')
