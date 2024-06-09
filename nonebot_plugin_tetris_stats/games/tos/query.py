from asyncio import gather
from datetime import timedelta
from http import HTTPStatus
from typing import Literal, NamedTuple

from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from nonebot_plugin_user import get_user  # type: ignore[import-untyped]
from nonebot_plugin_userinfo import EventUserInfo, UserInfo  # type: ignore[import-untyped]

from ...db import query_bind_info, trigger
from ...utils.exception import RequestError
from ...utils.host import HostPage, get_self_netloc
from ...utils.image import get_avatar
from ...utils.metrics import TetrisMetricsProWithLPMADPM, get_metrics
from ...utils.render import render
from ...utils.render.schemas.base import People, Ranking
from ...utils.render.schemas.tos_info import Info, Multiplayer, Radar
from ...utils.screenshot import screenshot
from ...utils.typing import Me, Number
from ..constant import CANT_VERIFY_MESSAGE
from . import alc
from .api import Player
from .api.schemas.user_info import UserInfoSuccess
from .constant import GAME_TYPE


def add_special_handlers(
    teaid_prefix: Literal['onebot-', 'kook-', 'discord-', 'qqguild-'], match_event: type[Event]
) -> None:
    @alc.assign('TOS.query')
    async def _(
        event: Event,
        target: At | Me,
        event_session: EventSession,
        event_user_info: UserInfo = EventUserInfo(),  # noqa: B008
    ):
        if isinstance(event, match_event):
            async with trigger(
                session_persist_id=await get_session_persist_id(event_session),
                game_platform=GAME_TYPE,
                command_type='query',
                command_args=[],
            ):
                player = Player(
                    teaid=f'{teaid_prefix}{target.target}'
                    if isinstance(target, At)
                    else f'{teaid_prefix}{event.get_user_id()}',
                    trust=True,
                )
                try:
                    user_info, game_data = await gather(player.get_info(), get_game_data(player))
                    if game_data is not None:
                        await UniMessage.image(
                            raw=await make_query_image(user_info, game_data, event_user_info)
                        ).finish()
                    await make_query_text(user_info, game_data).finish()
                except RequestError as e:
                    if e.status_code == HTTPStatus.BAD_REQUEST and '未找到此用户' in e.message:
                        return
                    raise


try:
    from nonebot.adapters.onebot.v11 import MessageEvent as OB11MessageEvent

    add_special_handlers('onebot-', OB11MessageEvent)
except ImportError:
    pass

try:
    from nonebot.adapters.qq.event import GuildMessageEvent as QQGuildMessageEvent
    from nonebot.adapters.qq.event import QQMessageEvent

    add_special_handlers('qqguild-', QQGuildMessageEvent)
    add_special_handlers('onebot-', QQMessageEvent)
except ImportError:
    pass

try:
    from nonebot.adapters.kaiheila.event import MessageEvent as KookMessageEvent

    add_special_handlers('kook-', KookMessageEvent)
except ImportError:
    pass

try:
    from nonebot.adapters.discord import MessageEvent as DiscordMessageEvent

    add_special_handlers('discord-', DiscordMessageEvent)
except ImportError:
    pass


@alc.assign('TOS.query')
async def _(
    event: Event,
    matcher: Matcher,
    target: At | Me,
    event_session: EventSession,
    event_user_info: UserInfo = EventUserInfo(),  # noqa: B008
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
                    event_session.platform, target.target if isinstance(target, At) else event.get_user_id()
                ),
                game_platform=GAME_TYPE,
            )
        if bind is None:
            await matcher.finish('未查询到绑定信息')
        message = CANT_VERIFY_MESSAGE
        player = Player(teaid=bind.game_account, trust=True)
        user_info, game_data = await gather(player.get_info(), get_game_data(player))
        if game_data is not None:
            await (
                message + UniMessage.image(raw=await make_query_image(user_info, game_data, event_user_info))
            ).finish()
        await (message + make_query_text(user_info, game_data)).finish()


@alc.assign('TOS.query')
async def _(account: Player, event_session: EventSession, event_user_info: UserInfo = EventUserInfo()):  # noqa: B008
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[],
    ):
        user_info, game_data = await gather(account.get_info(), get_game_data(account))
        if game_data is not None:
            await UniMessage.image(raw=await make_query_image(user_info, game_data, event_user_info)).finish()
        await make_query_text(user_info, game_data).finish()


class GameData(NamedTuple):
    game_num: int
    metrics: TetrisMetricsProWithLPMADPM
    OR: Number
    dspp: Number
    ge: Number


async def get_game_data(player: Player, query_num: int = 50) -> GameData | None:
    """获取游戏数据"""
    user_profile = await player.get_profile()
    if user_profile.data == []:
        return None
    weighted_total_lpm = weighted_total_apm = weighted_total_adpm = total_time = 0.0
    total_attack = total_dig = total_offset = total_pieses = total_receive = num = 0
    for i in user_profile.data:
        # 排除单人局和时间为0的游戏
        # 茶: 不计算没挖掘的局, 即使apm和lpm也如此
        if i.num_players == 1 or i.time == 0 or i.dig is None:
            continue
        # 加权计算
        time = i.time / 1000
        lpm = 24 * (i.pieces / time)
        apm = (i.attack / time) * 60
        adpm = ((i.attack + i.dig) / time) * 60
        weighted_total_lpm += lpm * time
        weighted_total_apm += apm * time
        weighted_total_adpm += adpm * time
        total_attack += i.attack
        total_dig += i.dig
        total_offset += i.offset
        total_pieses += i.pieces
        total_receive += i.receive
        total_time += time
        num += 1
        if num >= query_num:
            break
    if num == 0:
        return None
    # TODO: 如果有效局数小于 {查询数} , 并且没有无dig信息的局, 且 user_profile.data 内有{请求数}个局, 则继续往前获取信息
    metrics = get_metrics(
        lpm=weighted_total_lpm / total_time, apm=weighted_total_apm / total_time, adpm=weighted_total_adpm / total_time
    )
    return GameData(
        game_num=num,
        metrics=metrics,
        OR=total_offset / total_receive * 100,
        dspp=total_dig / total_pieses,
        ge=2 * ((total_attack * total_dig) / total_pieses**2),
    )


async def make_query_image(user_info: UserInfoSuccess, game_data: GameData, event_user_info: UserInfo) -> bytes:
    metrics = game_data.metrics
    duration = timedelta(milliseconds=float(user_info.data.pb_sprint)).total_seconds()
    sprint_value = f'{duration:.3f}s' if duration < 60 else f'{duration // 60:.0f}m {duration % 60:.3f}s'  # noqa: PLR2004
    async with HostPage(
        await render(
            'v1/tos/info',
            Info(
                user=People(avatar=await get_avatar(event_user_info, 'Data URI', None), name=user_info.data.name),
                ranking=Ranking(rating=float(user_info.data.ranking), rd=round(float(user_info.data.rd_now), 2)),
                multiplayer=Multiplayer(
                    pps=metrics.pps,
                    lpm=metrics.lpm,
                    apm=metrics.apm,
                    apl=metrics.apl,
                    vs=metrics.vs,
                    adpm=metrics.adpm,
                    adpl=metrics.adpl,
                ),
                radar=Radar(
                    app=(app := (metrics.apm / (60 * metrics.pps))),
                    OR=game_data.OR,
                    dspp=game_data.dspp,
                    ci=150 * game_data.dspp - 125 * app + 50 * (metrics.vs / metrics.apm) - 25,
                    ge=game_data.ge,
                ),
                sprint=sprint_value,
                challenge=f'{int(user_info.data.pb_challenge):,}' if user_info.data.pb_challenge != '0' else 'N/A',
                marathon=f'{int(user_info.data.pb_marathon):,}' if user_info.data.pb_marathon != '0' else 'N/A',
            ),
        )
    ) as page_hash:
        return await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html')


def make_query_text(user_info: UserInfoSuccess, game_data: GameData | None) -> UniMessage:
    user_data = user_info.data
    message = f'用户 {user_data.name} ({user_data.teaid}) '
    if user_data.ranked_games == '0':
        message += '暂无段位统计数据'
    else:
        message += f', 段位分 {round(float(user_data.rating_now),2)}±{round(float(user_data.rd_now),2)} ({round(float(user_data.vol_now),2)}) '
    if game_data is None:
        message += ', 暂无游戏数据'
    else:
        message += f', 最近 {game_data.game_num} 局数据'
        message += f"\nL'PM: {game_data.metrics.lpm} ( {game_data.metrics.pps} pps )"
        message += f'\nAPM: {game_data.metrics.apm} ( x{game_data.metrics.apl} )'
        message += f'\nADPM: {game_data.metrics.adpm} ( x{game_data.metrics.adpl} ) ( {game_data.metrics.vs}vs )'
    message += f'\n40L: {float(user_data.pb_sprint)/1000:.2f}s' if user_data.pb_sprint != '2147483647' else ''
    message += f'\nMarathon: {user_data.pb_marathon}' if user_data.pb_marathon != '0' else ''
    message += f'\nChallenge: {user_data.pb_challenge}' if user_data.pb_challenge != '0' else ''
    return UniMessage(message)
