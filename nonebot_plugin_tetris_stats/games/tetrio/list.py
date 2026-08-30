from typing import Annotated

from nonebot_plugin_alconna import Args, Option, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_uninfo.orm import get_session_persist_id

from ...db import trigger
from ...utils.lang import get_lang
from ...utils.metrics import get_metrics
from ...utils.render import render_image
from ...utils.render.schemas.v2.tetrio.user.list import Data, List, TetraLeague, User
from .. import alc
from . import command
from .constant import GAME_TYPE
from .rank.snapshot import LeagueListQuery, ListSort, query_league_list

command.add(
    Subcommand(
        'list',
        Option('--max-tr', Args['max_tr', float], help_text='TR的上限'),
        Option('--min-tr', Args['min_tr', float], help_text='TR的下限'),
        Option(
            '--limit',
            Args[
                'limit', Annotated[int, lambda x: 1 <= x <= 100]  # noqa: PLR2004
            ],
            help_text='查询数量',
        ),
        Option('--country', Args['country', str], help_text='国家代码'),
        Option('--sort', Args['sort', ListSort], help_text='排名指标'),
        help_text='查询 TETR.IO 段位排行榜',
    )
)


@alc.assign('TETRIO.list')
async def _(  # noqa: PLR0913, PLR0917
    event_session: Uninfo,
    max_tr: float | None = None,
    min_tr: float | None = None,
    limit: int | None = None,
    country: str | None = None,
    sort: ListSort | None = None,
):
    country = country.upper() if country is not None else None
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='list',
        command_args=[
            f'{key} {value}'
            for key, value in zip(
                ('--max-tr', '--min-tr', '--limit', '--country', '--sort'),
                (max_tr, min_tr, limit, country, sort),
                strict=True,
            )
            if value is not None
        ],
    ):
        async with get_session() as session:
            entries = await query_league_list(
                session,
                LeagueListQuery(
                    sort=sort or 'league',
                    max_tr=max_tr,
                    min_tr=min_tr,
                    limit=limit or 25,
                    country=country,
                ),
            )
        await UniMessage.image(
            raw=await render_image(
                List(
                    show_index=True,
                    data=[
                        Data(
                            user=User(
                                id=entry.id,
                                name=entry.username.upper(),
                                avatar=f'https://tetr.io/user-content/avatars/{entry.id}.jpg',
                                country=entry.country,
                                xp=entry.xp,
                            ),
                            tetra_league=TetraLeague(
                                rank=entry.league.rank,
                                tr=round(entry.league.tr, 2),
                                glicko=round(entry.league.glicko, 2),
                                rd=round(entry.league.rd, 2),
                                decaying=entry.league.decaying,
                                pps=(
                                    metrics := get_metrics(
                                        pps=entry.league.pps,
                                        apm=entry.league.apm,
                                        vs=entry.league.vs,
                                    )
                                ).pps,
                                apm=metrics.apm,
                                apl=metrics.apl,
                                vs=metrics.vs,
                                adpl=metrics.adpl,
                            ),
                        )
                        for entry in entries
                    ],
                    lang=get_lang(),
                ),
            )
        ).finish()
