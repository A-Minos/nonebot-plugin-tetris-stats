from asyncio import gather
from datetime import datetime, timedelta
from hashlib import md5

from yarl import URL

from ....utils.exception import FallbackError
from ....utils.host import HostPage, get_self_netloc
from ....utils.lang import get_lang
from ....utils.metrics import get_metrics
from ....utils.render import render
from ....utils.render.schemas.base import Avatar
from ....utils.render.schemas.v2.tetrio.user.info import (
    Achievement,
    Badge,
    Best,
    Blitz,
    Info,
    Sprint,
    Statistic,
    TetraLeague,
    TetraLeagueStatistic,
    User,
    Week,
    Zen,
    Zenith,
)
from ....utils.screenshot import screenshot
from ..api import Player
from ..api.schemas.summaries.league import InvalidData, NeverPlayedData, NeverRatedData
from .tools import flow_to_history, handling_special_value


async def make_query_image_v2(player: Player) -> bytes:
    (
        (user, user_info, league, sprint, blitz, zen),
        (avatar_revision, banner_revision, leagueflow, zenith, zenithex, achievements),
    ) = await gather(
        gather(
            player.user,
            player.get_info(),
            player.league,
            player.sprint,
            player.blitz,
            player.zen,
        ),
        gather(
            player.avatar_revision,
            player.banner_revision,
            player.get_leagueflow(),
            player.get_summaries('zenith'),
            player.get_summaries('zenithex'),
            player.get_summaries('achievements'),
        ),
    )
    if sprint.data.record is not None:
        duration = timedelta(milliseconds=sprint.data.record.results.stats.finaltime).total_seconds()
        sprint_value = f'{duration:.3f}s' if duration < 60 else f'{duration // 60:.0f}m {duration % 60:.3f}s'  # noqa: PLR2004
    else:
        sprint_value = 'N/A'

    play_time: str | None
    if (game_time := handling_special_value(user_info.data.gametime)) is not None:
        if game_time // 3600 > 0:
            play_time = f'{game_time // 3600:.0f}h {game_time % 3600 // 60:.0f}m {game_time % 60:.0f}s'
        elif game_time // 60 > 0:
            play_time = f'{game_time // 60:.0f}m {game_time % 60:.0f}s'
        else:
            play_time = f'{game_time:.0f}s'
    else:
        play_time = game_time
    try:
        history = flow_to_history(leagueflow, lambda x: x[-100:])
    except FallbackError:
        history = None
    netloc = get_self_netloc()
    async with HostPage(
        await render(
            'v2/tetrio/user/info',
            Info(
                user=User(
                    id=user.ID,
                    name=user.name.upper(),
                    country=user_info.data.country,
                    role=user_info.data.role,
                    botmaster=user_info.data.botmaster,
                    avatar=str(
                        URL(f'http://{netloc}/host/resource/tetrio/avatars/{user.ID}') % {'revision': avatar_revision}
                    )
                    if avatar_revision is not None and avatar_revision != 0
                    else Avatar(
                        type='identicon',
                        hash=md5(user.ID.encode()).hexdigest(),  # noqa: S324
                    ),
                    banner=str(
                        URL(f'http://{netloc}/host/resource/tetrio/banners/{user.ID}') % {'revision': banner_revision}
                    )
                    if banner_revision is not None and banner_revision != 0
                    else None,
                    bio=user_info.data.bio,
                    friend_count=user_info.data.friend_count,
                    supporter_tier=user_info.data.supporter_tier,
                    bad_standing=user_info.data.badstanding or False,
                    badges=[
                        Badge(
                            id=i.id,
                            description=i.label,
                            group=i.group,
                            receive_at=i.ts if isinstance(i.ts, datetime) else None,
                        )
                        for i in user_info.data.badges
                    ],
                    xp=user_info.data.xp,
                    ar=user_info.data.ar,
                    achievements=[
                        Achievement(
                            key=i.achievement_id,
                            rank_type=i.rank_type,
                            ar_type=i.ar_type,
                            stub=i.stub,
                            rank=i.rank,
                            achieved_score=i.achieved_score,
                            pos=i.pos,
                            progress=i.progress,
                            total=i.total,
                        )
                        for i in achievements.data
                    ],
                    playtime=play_time,
                    join_at=user_info.data.ts,
                ),
                tetra_league=TetraLeague(
                    rank=league.data.rank,
                    highest_rank='z' if isinstance(league.data, NeverRatedData) else league.data.bestrank,
                    tr=round(league.data.tr, 2),
                    glicko=round(league.data.glicko, 2),
                    rd=round(league.data.rd, 2),
                    global_rank=league.data.standing,
                    country_rank=league.data.standing_local,
                    pps=(metrics := get_metrics(pps=league.data.pps, apm=league.data.apm, vs=league.data.vs)).pps,
                    apm=metrics.apm,
                    apl=metrics.apl,
                    vs=metrics.vs,
                    adpl=metrics.adpl,
                    statistic=TetraLeagueStatistic(total=league.data.gamesplayed, wins=league.data.gameswon),
                    decaying=league.data.decaying,
                    history=history,
                )
                if not isinstance(league.data, NeverPlayedData | InvalidData)
                else None,
                zenith=Zenith(
                    week=Week(
                        altitude=zenith.data.record.results.stats.zenith.altitude,
                        global_rank=zenith.data.rank,
                        country_rank=zenith.data.rank_local,
                        play_at=zenith.data.record.ts,
                    )
                    if zenith.data.record is not None
                    else None,
                    best=Best(
                        altitude=zenith.data.best.record.results.stats.zenith.altitude,
                        global_rank=zenith.data.best.rank,
                        play_at=zenith.data.best.record.ts,
                    )
                    if zenith.data.best.record is not None
                    else None,
                ),
                zenithex=Zenith(
                    week=Week(
                        altitude=zenithex.data.record.results.stats.zenith.altitude,
                        global_rank=zenithex.data.rank,
                        country_rank=zenithex.data.rank_local,
                        play_at=zenithex.data.record.ts,
                    )
                    if zenithex.data.record is not None
                    else None,
                    best=Best(
                        altitude=zenithex.data.best.record.results.stats.zenith.altitude,
                        global_rank=zenithex.data.best.rank,
                        play_at=zenithex.data.best.record.ts,
                    )
                    if zenithex.data.best.record is not None
                    else None,
                ),
                statistic=Statistic(
                    total=handling_special_value(user_info.data.gamesplayed),
                    wins=handling_special_value(user_info.data.gameswon),
                ),
                sprint=Sprint(
                    time=sprint_value,
                    global_rank=sprint.data.rank,
                    country_rank=sprint.data.rank_local,
                    play_at=sprint.data.record.ts,
                )
                if sprint.data.record is not None
                else None,
                blitz=Blitz(
                    score=blitz.data.record.results.stats.score,
                    global_rank=blitz.data.rank,
                    country_rank=blitz.data.rank_local,
                    play_at=blitz.data.record.ts,
                )
                if blitz.data.record is not None
                else None,
                zen=Zen(level=zen.data.level, score=zen.data.score),
                lang=get_lang(),
            ),
        ),
    ) as page_hash:
        return await screenshot(f'http://{netloc}/host/{page_hash}.html')
