from nonebot_plugin_alconna import Args, Option, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_session import EventSession
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]

from ...db import trigger
from ...utils.host import HostPage, get_self_netloc
from ...utils.lang import get_lang
from ...utils.metrics import get_metrics
from ...utils.render import render
from ...utils.render.schemas.v2.tetrio.user.list import Data, List, TetraLeague, User
from ...utils.screenshot import screenshot
from .. import alc
from . import command
from .api.leaderboards import by
from .api.schemas.base import P
from .api.schemas.leaderboards import Parameter
from .api.schemas.leaderboards.by import Entry
from .constant import GAME_TYPE

command.add(
    Subcommand(
        'list',
        Option('--max-tr', Args['max_tr', float], help_text='TR的上限'),
        Option('--min-tr', Args['min_tr', float], help_text='TR的下限'),
        Option('--limit', Args['limit', int], help_text='查询数量'),
        Option('--country', Args['country', str], help_text='国家代码'),
        help_text='查询 TETR.IO 段位排行榜',
    )
)


@alc.assign('TETRIO.list')
async def _(
    event_session: EventSession,
    max_tr: float | None = None,
    min_tr: float | None = None,
    limit: int | None = None,
    country: str | None = None,
):
    country = country.upper() if country is not None else None
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
        parameter = Parameter(
            # ?: 似乎是只需要 pri 至少 league 榜的返回值只有 pri
            after=P(pri=max_tr, sec=0, ter=0).to_prisecter() if max_tr is not None else None,
            before=P(pri=min_tr, sec=0, ter=0).to_prisecter() if min_tr is not None else None,
            limit=limit or 25,
            country=country,
        )
        league = await by('league', parameter)
        async with HostPage(
            await render(
                'v2/tetrio/user/list',
                List(
                    show_index=True,
                    data=[
                        Data(
                            user=User(
                                id=i.id,
                                name=i.username.upper(),
                                avatar=f'https://tetr.io/user-content/avatars/{i.id}.jpg',
                                country=i.country,
                                xp=i.xp,
                            ),
                            tetra_league=TetraLeague(
                                rank=i.league.rank,
                                tr=round(i.league.tr, 2),
                                glicko=round(i.league.glicko, 2),
                                rd=round(i.league.rd, 2),
                                decaying=i.league.decaying,
                                pps=(metrics := get_metrics(pps=i.league.pps, apm=i.league.apm, vs=i.league.vs)).pps,
                                apm=metrics.apm,
                                apl=metrics.apl,
                                vs=metrics.vs,
                                adpl=metrics.adpl,
                            ),
                        )
                        for i in league.data.entries
                        if isinstance(i, Entry)
                    ],
                    lang=get_lang(),
                ),
            )
        ) as page_hash:
            await UniMessage.image(raw=await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html')).finish()
