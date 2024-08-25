from asyncio import gather
from datetime import datetime, timedelta, timezone
from hashlib import md5
from typing import TypeVar

from arclet.alconna import Arg, ArgFlag
from nonebot import get_driver
from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import Args, At, Option, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from nonebot_plugin_user import User as NBUser
from nonebot_plugin_user import get_user
from sqlalchemy import select
from yarl import URL

from ...db import query_bind_info, trigger
from ...utils.host import HostPage, get_self_netloc
from ...utils.metrics import get_metrics
from ...utils.render import render
from ...utils.render.schemas.base import Avatar
from ...utils.render.schemas.tetrio.user.info_v2 import (
    Badge,
    Blitz,
    Sprint,
    Statistic,
    TetraLeague,
    TetraLeagueStatistic,
    Zen,
)
from ...utils.render.schemas.tetrio.user.info_v2 import Info as V2TemplateInfo
from ...utils.render.schemas.tetrio.user.info_v2 import User as V2TemplateUser
from ...utils.screenshot import screenshot
from ...utils.typing import Me
from .. import add_block_handlers, alc
from ..constant import CANT_VERIFY_MESSAGE
from . import command, get_player
from .api import Player
from .api.schemas.summaries.league import NeverPlayedData, NeverRatedData
from .constant import GAME_TYPE
from .models import TETRIOUserConfig
from .typing import Template

UTC = timezone.utc

driver = get_driver()

command.add(
    Subcommand(
        'query',
        Args(
            Arg(
                'target',
                At | Me,
                notice='@想要查询的人 / 自己',
                flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
            ),
            Arg(
                'account',
                get_player,
                notice='TETR.IO 用户名 / ID',
                flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
            ),
        ),
        Option(
            '--template',
            Arg('template', Template),
            alias=['-T'],
            help_text='要使用的查询模板',
        ),
        help_text='查询 TETR.IO 游戏信息',
    ),
)

alc.shortcut(
    '(?i:io)(?i:查询|查|query|stats)',
    command='tstats TETR.IO query',
    humanized='io查',
)
alc.shortcut(
    'fkosk',
    command='tstats TETR.IO query',
    arguments=['我'],
    fuzzy=False,
    humanized='An Easter egg!',
)

add_block_handlers(alc.assign('TETRIO.query'))


@alc.assign('TETRIO.query')
async def _(  # noqa: PLR0913
    user: NBUser,
    event: Event,
    matcher: Matcher,
    target: At | Me,
    event_session: EventSession,
    template: Template | None = None,
):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[f'--default-template {template}'] if template is not None else [],
    ):
        async with get_session() as session:
            bind = await query_bind_info(
                session=session,
                user=await get_user(
                    event_session.platform, target.target if isinstance(target, At) else event.get_user_id()
                ),
                game_platform=GAME_TYPE,
            )
            if template is None:
                template = await session.scalar(
                    select(TETRIOUserConfig.query_template).where(TETRIOUserConfig.id == user.id)
                )
        if bind is None:
            await matcher.finish('未查询到绑定信息')
        message = UniMessage(CANT_VERIFY_MESSAGE)
        player = Player(user_id=bind.game_account, trust=True)
        await (message + UniMessage.image(raw=await make_query_image_v2(player))).finish()


@alc.assign('TETRIO.query')
async def _(user: NBUser, account: Player, event_session: EventSession, template: Template | None = None):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[f'--default-template {template}'] if template is not None else [],
    ):
        async with get_session() as session:
            if template is None:
                template = await session.scalar(
                    select(TETRIOUserConfig.query_template).where(TETRIOUserConfig.id == user.id)
                )
        await (UniMessage.image(raw=await make_query_image_v2(account))).finish()


N = TypeVar('N', int, float)


def handling_special_value(value: N) -> N | None:
    return value if value != -1 else None


async def make_query_image_v2(player: Player) -> bytes:
    (
        (user, user_info, league, sprint, blitz, zen),
        (avatar_revision, banner_revision),
    ) = await gather(
        gather(player.user, player.get_info(), player.league, player.sprint, player.blitz, player.zen),
        gather(player.avatar_revision, player.banner_revision),
    )
    if sprint.data.record is not None:
        duration = timedelta(milliseconds=sprint.data.record.results.stats.finaltime).total_seconds()
        sprint_value = f'{duration:.3f}s' if duration < 60 else f'{duration // 60:.0f}m {duration % 60:.3f}s'  # noqa: PLR2004
    else:
        sprint_value = 'N/A'

    play_time: str | None
    if (game_time := handling_special_value(user_info.data.gametime)) is not None:
        if game_time // 3600 > 0:
            play_time = f'{game_time//3600:.0f}h {game_time % 3600 // 60:.0f}m {game_time % 60:.0f}s'
        elif game_time // 60 > 0:
            play_time = f'{game_time//60:.0f}m {game_time % 60:.0f}s'
        else:
            play_time = f'{game_time:.0f}s'
    else:
        play_time = game_time
    netloc = get_self_netloc()
    async with HostPage(
        await render(
            'v2/tetrio/user/info',
            V2TemplateInfo(
                user=V2TemplateUser(
                    id=user.ID,
                    name=user.name.upper(),
                    bio=user_info.data.bio,
                    banner=str(
                        URL(f'http://{netloc}/host/resource/tetrio/banners/{user.ID}') % {'revision': banner_revision}
                    )
                    if banner_revision is not None and banner_revision != 0
                    else None,
                    avatar=str(
                        URL(f'http://{netloc}/host/resource/tetrio/avatars/{user.ID}') % {'revision': avatar_revision}
                    )
                    if avatar_revision is not None and avatar_revision != 0
                    else Avatar(
                        type='identicon',
                        hash=md5(user.ID.encode()).hexdigest(),  # noqa: S324
                    ),
                    badges=[
                        Badge(
                            id=i.id,
                            description=i.label,
                            group=i.group,
                            receive_at=i.ts if isinstance(i.ts, datetime) else None,
                        )
                        for i in user_info.data.badges
                    ],
                    country=user_info.data.country,
                    role=user_info.data.role,
                    xp=user_info.data.xp,
                    friend_count=user_info.data.friend_count,
                    supporter_tier=user_info.data.supporter_tier,
                    bad_standing=user_info.data.badstanding or False,
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
                    history=None,
                )
                if not isinstance(league.data, NeverPlayedData)
                else None,
                statistic=Statistic(
                    total=handling_special_value(user_info.data.gamesplayed),
                    wins=handling_special_value(user_info.data.gameswon),
                ),
                sprint=Sprint(
                    time=sprint_value,
                    global_rank=sprint.data.rank,
                    play_at=sprint.data.record.ts,
                )
                if sprint.data.record is not None
                else None,
                blitz=Blitz(
                    score=blitz.data.record.results.stats.score,
                    global_rank=blitz.data.rank,
                    play_at=blitz.data.record.ts,
                )
                if blitz.data.record is not None
                else None,
                zen=Zen(level=zen.data.level, score=zen.data.score),
            ),
        ),
    ) as page_hash:
        return await screenshot(f'http://{netloc}/host/{page_hash}.html')
