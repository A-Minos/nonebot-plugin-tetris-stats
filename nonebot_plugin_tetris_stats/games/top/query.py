from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from nonebot_plugin_user import get_user  # type: ignore[import-untyped]

from ...db import query_bind_info, trigger
from ...utils.metrics import get_metrics
from ...utils.typing import Me
from ..constant import CANT_VERIFY_MESSAGE
from . import alc
from .api import Player
from .api.schemas.user_profile import UserProfile
from .constant import GAME_TYPE


@alc.assign('TOP.query')
async def _(event: Event, matcher: Matcher, target: At | Me, event_session: EventSession):
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
        await (message + make_query_text(await Player(user_name=bind.game_account, trust=True).get_profile())).finish()


@alc.assign('TOP.query')
async def _(account: Player, event_session: EventSession):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[],
    ):
        await (make_query_text(await account.get_profile())).finish()


def make_query_text(profile: UserProfile) -> UniMessage:
    message = ''
    if profile.today is not None:
        today = get_metrics(lpm=profile.today.lpm, apm=profile.today.apm)
        message += f'用户 {profile.user_name} 24小时内统计数据为: '
        message += f"\nL'PM: {today.lpm} ( {today.pps} pps )"
        message += f'\nAPM: {today.apm} ( x{today.apl} )'
    else:
        message += f'用户 {profile.user_name} 暂无24小时内统计数据'
    if profile.total is not None:
        total_lpm = total_apm = 0.0
        for value in profile.total:
            total_lpm += value.lpm
            total_apm += value.apm
        num = len(profile.total)
        total = get_metrics(lpm=total_lpm / num, apm=total_apm / num)
        message += '\n历史统计数据为: '
        message += f"\nL'PM: {total.lpm} ( {total.pps} pps )"
        message += f'\nAPM: {total.apm} ( x{total.apl} )'
    else:
        message += '\n暂无历史统计数据'
    return UniMessage(message)
