from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]

from ...db import trigger
from ...utils.host import HostPage, get_self_netloc
from ...utils.metrics import get_metrics
from ...utils.render import render
from ...utils.render.schemas.tetrio.tetrio_user_list_v2 import List, TetraLeague, User
from ...utils.screenshot import screenshot
from .. import alc
from .api.schemas.tetra_league import ValidLeague
from .api.tetra_league import Parameter, leaderboard
from .constant import GAME_TYPE


@alc.assign('TETRIO.list')
async def _(
    event_session: EventSession,
    max_tr: float | None = None,
    min_tr: float | None = None,
    limit: int | None = None,
    country: str | None = None,
):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='list',
        command_args=[
            f'{key} {value}'
            for key, value in zip(
                ('--max-tr', '--min-tr', '--limit', '--country'), (max_tr, min_tr, limit, country), strict=True
            )
            if value is not None
        ],
    ):
        parameter: Parameter = {}
        if max_tr is not None:
            parameter['after'] = max_tr
        if min_tr is not None:
            parameter['before'] = min_tr
        if limit is not None:
            parameter['limit'] = limit
        if country is not None:
            parameter['country'] = country
        league = await leaderboard(parameter)
        async with HostPage(
            await render(
                'v2/tetrio/user/list',
                List(
                    show_index=True,
                    users=[
                        User(
                            id=i.id,
                            name=i.username.upper(),
                            avatar=f'https://tetr.io/user-content/avatars/{i.id}.jpg',
                            country=i.country,
                            verified=i.verified,
                            tetra_league=TetraLeague(
                                rank=i.league.rank,
                                tr=round(i.league.rating, 2),
                                glicko=round(i.league.glicko, 2),
                                rd=round(i.league.rd, 2),
                                decaying=i.league.decaying,
                                pps=(metrics := get_metrics(pps=i.league.pps, apm=i.league.apm, vs=i.league.vs)).pps,
                                apm=metrics.apm,
                                apl=metrics.apl,
                                vs=metrics.vs,
                                adpl=metrics.adpl,
                            ),
                            xp=i.xp,
                            join_at=None,
                        )
                        for i in league.data.users
                        if isinstance(i.league, ValidLeague)
                    ],
                ),
            )
        ) as page_hash:
            await UniMessage.image(raw=await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html')).finish()
