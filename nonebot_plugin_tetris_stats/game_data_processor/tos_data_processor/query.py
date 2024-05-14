from asyncio import gather
from dataclasses import dataclass
from typing import Literal

from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]

from ...db import query_bind_info, trigger
from ...utils.metrics import TetrisMetricsProWithLPMADPM, get_metrics
from ...utils.platform import get_platform
from ...utils.typing import Me
from ..constant import CANT_VERIFY_MESSAGE
from . import alc
from .api import Player
from .constant import GAME_TYPE


def add_special_handlers(
    teaid_prefix: Literal['onebot-', 'kook-', 'discord-', 'qqguild-'], match_event: type[Event]
) -> None:
    @alc.assign('query')
    async def _(event: Event, target: At | Me, event_session: EventSession):
        if isinstance(event, match_event):
            async with trigger(
                session_persist_id=await get_session_persist_id(event_session),
                game_platform=GAME_TYPE,
                command_type='query',
                command_args=[],
            ):
                await (
                    await make_query_text(
                        Player(
                            teaid=f'{teaid_prefix}{target.target}'
                            if isinstance(target, At)
                            else f'{teaid_prefix}{event.get_user_id()}',
                            trust=True,
                        )
                    )
                ).finish()


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


@alc.assign('query')
async def _(bot: Bot, event: Event, matcher: Matcher, target: At | Me, event_session: EventSession):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[],
    ):
        async with get_session() as session:
            bind = await query_bind_info(
                session=session,
                chat_platform=get_platform(bot),
                chat_account=(target.target if isinstance(target, At) else event.get_user_id()),
                game_platform=GAME_TYPE,
            )
        if bind is None:
            await matcher.finish('未查询到绑定信息')
        message = CANT_VERIFY_MESSAGE
        await (message + await make_query_text(Player(teaid=bind.game_account, trust=True))).finish()


@alc.assign('query')
async def _(account: Player, event_session: EventSession):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[],
    ):
        await (await make_query_text(account)).finish()


@dataclass
class GameData:
    game_num: int
    metrics: TetrisMetricsProWithLPMADPM


async def get_game_data(player: Player, query_num: int = 50) -> GameData | None:
    """获取游戏数据"""
    user_profile = await player.get_profile()
    if user_profile.data == []:
        return None
    weighted_total_lpm = weighted_total_apm = weighted_total_adpm = total_time = 0.0
    num = 0
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
    lpm = weighted_total_lpm / total_time
    apm = weighted_total_apm / total_time
    adpm = weighted_total_adpm / total_time
    return GameData(game_num=num, metrics=metrics)


async def make_query_text(player: Player) -> UniMessage:
    user_info, game_data = await gather(player.get_info(), get_game_data(player))
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
