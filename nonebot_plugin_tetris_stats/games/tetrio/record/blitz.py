from asyncio import gather
from datetime import timedelta
from hashlib import md5
from urllib.parse import urlencode

from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_user import get_user  # type: ignore[import-untyped]

from ....db import query_bind_info
from ....utils.exception import RecordNotFoundError
from ....utils.host import HostPage, get_self_netloc
from ....utils.metrics import get_metrics
from ....utils.render import render
from ....utils.render.schemas.base import Avatar
from ....utils.render.schemas.tetrio.tetrio_record_base import Finesse, Max, Mini, Tspins, User
from ....utils.render.schemas.tetrio.tetrio_record_blitz import Record, Statistic
from ....utils.screenshot import screenshot
from ....utils.typing import Me
from ...constant import CANT_VERIFY_MESSAGE
from .. import alc
from ..api.player import Player
from ..constant import GAME_TYPE


@alc.assign('TETRIO.record.blitz')
async def _(
    event: Event,
    matcher: Matcher,
    target: At | Me,
    event_session: EventSession,
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
    message = UniMessage(CANT_VERIFY_MESSAGE)
    player = Player(user_id=bind.game_account, trust=True)
    await (message + UniMessage.image(raw=await make_blitz_image(player))).finish()


@alc.assign('TETRIO.record.blitz')
async def _(account: Player):
    await UniMessage.image(raw=await make_blitz_image(account)).finish()


async def make_blitz_image(player: Player) -> bytes:
    user, user_info, blitz = await gather(player.user, player.get_info(), player.blitz)
    if blitz.record is None:
        msg = f'未找到用户 {user.name.upper()} 的 Blitz 记录'
        raise RecordNotFoundError(msg)
    endcontext = blitz.record.endcontext
    clears = endcontext.clears
    duration = timedelta(milliseconds=endcontext.final_time).total_seconds()
    metrics = get_metrics(pps=endcontext.piecesplaced / duration)
    netloc = get_self_netloc()
    async with HostPage(
        page=await render(
            'v2/tetrio/record/blitz',
            Record(
                user=User(
                    id=user.ID,
                    name=user.name.upper(),
                    avatar=f'http://{netloc}/host/resource/tetrio/avatars/{user.ID}?{urlencode({"revision": user_info.data.user.avatar_revision})}'
                    if user_info.data.user.avatar_revision is not None and user_info.data.user.avatar_revision != 0
                    else Avatar(
                        type='identicon',
                        hash=md5(user.ID.encode()).hexdigest(),  # noqa: S324
                    ),
                ),
                replay_id=blitz.record.replayid,
                rank=blitz.rank,
                statistic=Statistic(
                    keys=endcontext.inputs,
                    kpp=round(endcontext.inputs / endcontext.piecesplaced, 2),
                    kps=round(endcontext.inputs / duration, 2),
                    max=Max(
                        combo=max((0, endcontext.topcombo - 1)),
                        btb=max((0, endcontext.topbtb - 1)),
                    ),
                    pieces=endcontext.piecesplaced,
                    pps=metrics.pps,
                    lines=endcontext.lines,
                    lpm=metrics.lpm,
                    holds=endcontext.holds,
                    score=endcontext.score,
                    spp=round(endcontext.score / endcontext.piecesplaced, 2),
                    single=clears.singles,
                    double=clears.doubles,
                    triple=clears.triples,
                    quad=clears.quads,
                    tspins=Tspins(
                        total=clears.realtspins,
                        single=clears.tspinsingles,
                        double=clears.tspindoubles,
                        triple=clears.triples,
                        mini=Mini(
                            total=clears.minitspins,
                            single=clears.minitspinsingles,
                            double=clears.minitspindoubles,
                        ),
                    ),
                    all_clear=clears.allclear,
                    finesse=Finesse(
                        faults=endcontext.finesse.faults,
                        accuracy=round(endcontext.finesse.perfectpieces / endcontext.piecesplaced * 100, 2),
                    ),
                    level=endcontext.level,
                ),
                play_at=blitz.record.ts,
            ),
        )
    ) as page_hash:
        return await screenshot(f'http://{netloc}/host/{page_hash}.html')
