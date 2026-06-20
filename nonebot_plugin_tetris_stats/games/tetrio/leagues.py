from arclet.alconna import Arg, ArgFlag
from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import Args, At, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_uninfo.orm import get_session_persist_id
from nonebot_plugin_user import get_user

from ...db import query_bind_info, trigger
from ...i18n import Lang
from ...utils.lang import get_lang
from ...utils.metrics import get_metrics
from ...utils.render import render_image
from ...utils.render.schemas.v2.tetrio.tetra_league import Data, Game, StatisticalData, User
from ...utils.typedefs import Me
from . import alc, command, get_player
from .api import Player
from .api.player import RecordModeType, RecordType
from .constant import GAME_TYPE

command.add(
    Subcommand(
        'leagues',
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
        alias=['tl', '联赛'],
        help_text='查看 TETR.IO 联赛信息',
    )
)

alc.shortcut(
    '(?i:io)(?i:联赛|league|tl)',
    command='tstats TETR.IO leagues',
    humanized='io联赛',
)


@alc.assign('TETRIO.leagues')
async def _(
    event: Event,
    matcher: Matcher,
    target: At | Me,
    event_session: Uninfo,
):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[],
    ):
        async with get_session() as session:
            bind = await query_bind_info(
                session=session,
                user=await get_user(
                    event_session.scope, target.target if isinstance(target, At) else event.get_user_id()
                ),
                game_platform=GAME_TYPE,
            )
        if bind is None:
            await matcher.finish(Lang.bind.not_found())
        player = Player(user_id=bind.game_account, trust=True)
        await (await make_result(player)).finish()


@alc.assign('TETRIO.leagues')
async def _(
    account: Player,
    event_session: Uninfo,
):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[],
    ):
        await (await make_result(account)).finish()


async def make_result(player: Player) -> UniMessage:
    records = await player.get_records(RecordModeType.League, RecordType.Recent)
    last = records.data.entries[0]
    return UniMessage.image(
        raw=await render_image(
            Data(
                replay_id=last.replayid,
                games=[
                    Game(
                        user=User(id=i.id, name=i.username),
                        points=i.wins,
                        average_data=StatisticalData(
                            pps=(metrics := get_metrics(pps=i.stats.pps, apm=i.stats.apm, vs=i.stats.vsscore)).pps,
                            apm=metrics.apm,
                            apl=metrics.apl,
                            vs=metrics.vs,
                            adpl=metrics.adpl,
                        ),
                        data=[
                            StatisticalData(
                                pps=(metrics := get_metrics(pps=j.stats.pps, apm=j.stats.apm, vs=j.stats.vsscore)).pps,
                                apm=metrics.apm,
                                apl=metrics.apl,
                                vs=metrics.vs,
                                adpl=metrics.adpl,
                            )
                            for _round in last.results.rounds
                            for j in _round
                            if j.id == i.id
                        ],
                    )
                    for i in last.results.leaderboard
                ],
                play_at=last.ts,
                lang=get_lang(),
            ),
        )
    )
