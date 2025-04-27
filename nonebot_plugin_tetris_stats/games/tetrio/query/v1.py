from asyncio import gather
from datetime import timedelta
from hashlib import md5

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
from ..api.schemas.summaries.league import RatedData
from ..constant import TR_MAX, TR_MIN
from .tools import flow_to_history, get_league_data


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
                    lpm_trending=Trending.KEEP,
                    apm=metrics.apm,
                    apl=metrics.apl,
                    apm_trending=Trending.KEEP,
                    adpm=metrics.adpm,
                    vs=metrics.vs,
                    adpl=metrics.adpl,
                    adpm_trending=Trending.KEEP,
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
