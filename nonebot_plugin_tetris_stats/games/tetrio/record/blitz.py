from asyncio import gather
from contextlib import suppress
from datetime import timedelta
from hashlib import md5

from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At, Option
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_uninfo.orm import get_session_persist_id
from nonebot_plugin_user import get_user
from yarl import URL

from ....db import query_bind_info, trigger
from ....i18n import Lang
from ....utils.exception import RecordNotFoundError, RequestError
from ....utils.host import get_self_netloc
from ....utils.lang import get_lang
from ....utils.metrics import get_metrics
from ....utils.render import render_image
from ....utils.render.schemas.base import Avatar
from ....utils.render.schemas.v2.tetrio.record.base import Finesse, Max, Mini, RecordQuery, Tspins, User
from ....utils.render.schemas.v2.tetrio.record.blitz import Record, Statistic
from ....utils.typedefs import Me
from .. import alc, assign
from ..alias import PlayerDep
from ..api.player import Player, RecordModeType, RecordType
from ..constant import GAME_TYPE
from ..mask import display_name, get_mask
from . import command

command.add(Option('--blitz', dest='blitz', help_text=Lang.command.tetrio.record.options.blitz.help.cast()))

alc.shortcut(
    '(?i:io)(?i:记录|record)(?i:blitz)',
    command='tstats TETR.IO record --blitz',
    humanized=Lang.command.tetrio.record.shortcuts.blitz.cast(),
)


@assign('TETRIO.record.blitz')
async def _(  # noqa: PLR0913, PLR0917
    event: Event,
    matcher: Matcher,
    who: At | Me,
    event_session: Uninfo,
    record_type: RecordType | None = None,
    index: int | None = None,
):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='record',
        command_args=['--blitz']
        + ([f'--type {record_type.value}'] if record_type is not None else [])
        + ([f'--index {index}'] if index is not None else []),
    ):
        async with get_session() as session:
            bind = await query_bind_info(
                session=session,
                user=await get_user(event_session.scope, who.target if isinstance(who, At) else event.get_user_id()),
                game_platform=GAME_TYPE,
            )
        if bind is None:
            await matcher.finish(Lang.bind.not_found())
        player = Player(user_id=bind.game_account, trust=True)
        await (
            (UniMessage.i18n(Lang.interaction.warning.unverified) if not bind.verify else UniMessage())
            + UniMessage.image(raw=await make_blitz_image(player, record_type, index))
        ).finish()


@assign('TETRIO.record.blitz')
async def _(
    event_session: Uninfo,
    player: PlayerDep,
    record_type: RecordType | None = None,
    index: int | None = None,
):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='record',
        command_args=['--blitz']
        + ([f'--type {record_type.value}'] if record_type is not None else [])
        + ([f'--index {index}'] if index is not None else []),
    ):
        await UniMessage.image(raw=await make_blitz_image(player, record_type, index)).finish()


async def make_blitz_image(
    player: Player,
    record_type: RecordType | None = None,
    index: int | None = None,
) -> bytes:
    user, record = await gather(
        player.user,
        player.get_record(RecordModeType.Blitz, record_type, index=index),
    )
    if record is None:
        msg = Lang.record.not_found(
            username=display_name(user.name.upper(), await get_mask(user.ID)), mode=Lang.record.blitz()
        )
        raise RecordNotFoundError(msg)
    global_rank: int | None = None
    country_rank: int | None = None
    with suppress(RequestError):
        summary = (await player.blitz).data
        if summary.record is not None and summary.record.id == record.id:
            global_rank = summary.rank if summary.rank > 0 else None
            country_rank = summary.rank_local if summary.rank_local > 0 else None

    stats = record.results.stats
    clears = stats.clears
    duration = timedelta(milliseconds=stats.finaltime).total_seconds()
    metrics = get_metrics(pps=stats.piecesplaced / duration)
    return await render_image(
        Record(
            query=RecordQuery(type=record_type or RecordType.Top, index=1 if index is None else index),
            user=User(
                id=user.ID,
                name=user.name.upper(),
                country=await player.country,
                avatar=str(
                    URL(f'http://{get_self_netloc()}/host/resource/tetrio/avatars/{user.ID}')
                    % {'revision': avatar_revision}
                )
                if (avatar_revision := (await player.avatar_revision)) is not None and avatar_revision != 0
                else Avatar(
                    type='identicon',
                    hash=md5(user.ID.encode()).hexdigest(),  # noqa: S324
                ),
            ),
            replay_id=record.replayid,
            global_rank=global_rank,
            country_rank=country_rank,
            personal_best='current' if record.pb else 'former' if record.oncepb else None,
            disputed=record.disputed,
            statistic=Statistic(
                keys=stats.inputs,
                kpp=round(stats.inputs / stats.piecesplaced, 2),
                kps=round(stats.inputs / duration, 2),
                max=Max(
                    combo=max((0, stats.topcombo - 1)),
                    btb=max((0, stats.topbtb - 1)),
                ),
                pieces=stats.piecesplaced,
                pps=metrics.pps,
                lines=stats.lines,
                lpm=metrics.lpm,
                holds=stats.holds,
                score=stats.score,
                spp=round(stats.score / stats.piecesplaced, 2),
                single=clears.singles,
                double=clears.doubles,
                triple=clears.triples,
                quad=clears.quads,
                tspins=Tspins(
                    total=clears.realtspins,
                    single=clears.tspinsingles,
                    double=clears.tspindoubles,
                    triple=clears.tspintriples,
                    mini=Mini(
                        total=clears.minitspins,
                        single=clears.minitspinsingles,
                        double=clears.minitspindoubles,
                    ),
                ),
                all_clear=clears.allclear,
                finesse=Finesse(
                    faults=stats.finesse.faults,
                    accuracy=round(stats.finesse.perfectpieces / stats.piecesplaced * 100, 2),
                ),
                level=stats.level,
            ),
            play_at=record.ts,
            lang=get_lang(),
        ),
    )
