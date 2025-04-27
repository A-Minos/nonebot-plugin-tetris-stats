from asyncio import gather
from datetime import timedelta
from hashlib import md5

from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At, Option
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from nonebot_plugin_user import get_user
from yarl import URL

from ....db import query_bind_info, trigger
from ....i18n import Lang
from ....utils.exception import RecordNotFoundError
from ....utils.host import HostPage, get_self_netloc
from ....utils.lang import get_lang
from ....utils.metrics import get_metrics
from ....utils.render import render
from ....utils.render.schemas.base import Avatar
from ....utils.render.schemas.v2.tetrio.record.base import Finesse, Max, Mini, Statistic, Tspins, User
from ....utils.render.schemas.v2.tetrio.record.sprint import Record
from ....utils.screenshot import screenshot
from ....utils.typedefs import Me
from .. import alc
from ..api.player import Player
from ..constant import GAME_TYPE
from . import command

command.add(Option('--40l', dest='sprint'))

alc.shortcut(
    '(?i:io)(?i:记录|record)(?i:40l)',
    command='tstats TETR.IO record --40l',
    humanized='io记录40l',
)


@alc.assign('TETRIO.record.sprint')
async def _(
    event: Event,
    matcher: Matcher,
    target: At | Me,
    event_session: EventSession,
):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='record',
        command_args=['--40l'],
    ):
        async with get_session() as session:
            bind = await query_bind_info(
                session=session,
                user=await get_user(
                    event_session.platform, target.target if isinstance(target, At) else event.get_user_id()
                ),
                game_platform=GAME_TYPE,
            )
        if bind is None:
            await matcher.finish('未查询到绑定信息')
        player = Player(user_id=bind.game_account, trust=True)
        await (
            UniMessage.i18n(Lang.interaction.warning.unverified) + UniMessage.image(raw=await make_sprint_image(player))
        ).finish()


@alc.assign('TETRIO.record.sprint')
async def _(account: Player, event_session: EventSession):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='record',
        command_args=['--40l'],
    ):
        await UniMessage.image(raw=await make_sprint_image(account)).finish()


async def make_sprint_image(player: Player) -> bytes:
    user, sprint = await gather(player.user, player.sprint)
    if sprint.data.record is None:
        msg = f'未找到用户 {user.name.upper()} 的 40L 记录'
        raise RecordNotFoundError(msg)
    stats = sprint.data.record.results.stats
    clears = stats.clears
    duration = timedelta(milliseconds=stats.finaltime).total_seconds()
    sprint_value = f'{duration:.3f}s' if duration < 60 else f'{duration // 60:.0f}m {duration % 60:.3f}s'  # noqa: PLR2004
    metrics = get_metrics(pps=stats.piecesplaced / duration)
    netloc = get_self_netloc()
    async with HostPage(
        page=await render(
            'v2/tetrio/record/sprint',
            Record(
                type='best',
                user=User(
                    id=user.ID,
                    name=user.name.upper(),
                    avatar=str(
                        URL(f'http://{netloc}/host/resource/tetrio/avatars/{user.ID}') % {'revision': avatar_revision}
                    )
                    if (avatar_revision := (await player.avatar_revision)) is not None and avatar_revision != 0
                    else Avatar(
                        type='identicon',
                        hash=md5(user.ID.encode()).hexdigest(),  # noqa: S324
                    ),
                ),
                time=sprint_value,
                replay_id=sprint.data.record.replayid,
                rank=sprint.data.rank,
                personal_rank=1,
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
                ),
                play_at=sprint.data.record.ts,
                lang=get_lang(),
            ),
        )
    ) as page_hash:
        return await screenshot(f'http://{netloc}/host/{page_hash}.html')
