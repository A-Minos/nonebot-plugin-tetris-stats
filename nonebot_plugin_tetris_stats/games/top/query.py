from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from nonebot_plugin_user import get_user

from ...db import query_bind_info, trigger
from ...i18n import Lang
from ...utils.exception import FallbackError
from ...utils.host import HostPage, get_self_netloc
from ...utils.lang import get_lang
from ...utils.metrics import TetrisMetricsBasicWithLPM, get_metrics
from ...utils.render import render
from ...utils.render.avatar import get_avatar
from ...utils.render.schemas.base import People, Trending
from ...utils.render.schemas.v1.top.info import Data as InfoData
from ...utils.render.schemas.v1.top.info import Info
from ...utils.screenshot import screenshot
from ...utils.typedefs import Me
from . import alc
from .api import Player
from .api.schemas.user_profile import Data, UserProfile
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
        await (
            UniMessage.i18n(Lang.interaction.warning.unverified)
            + await make_query_result(await Player(user_name=bind.game_account, trust=True).get_profile())
        ).finish()


@alc.assign('TOP.query')
async def _(account: Player, event_session: EventSession):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[],
    ):
        await (await make_query_result(await account.get_profile())).finish()


def get_avg_metrics(data: list[Data]) -> TetrisMetricsBasicWithLPM:
    total_lpm = total_apm = 0.0
    for value in data:
        total_lpm += value.lpm
        total_apm += value.apm
    num = len(data)
    return get_metrics(lpm=total_lpm / num, apm=total_apm / num)


async def make_query_image(profile: UserProfile) -> bytes:
    if profile.today is None or profile.total is None:
        raise FallbackError
    today = get_metrics(lpm=profile.today.lpm, apm=profile.today.apm)
    history = get_avg_metrics(profile.total)
    async with HostPage(
        await render(
            'v1/top/info',
            Info(
                user=People(avatar=get_avatar(profile.user_name), name=profile.user_name),
                today=InfoData(
                    pps=today.pps,
                    lpm=today.lpm,
                    lpm_trending=Trending.KEEP,
                    apm=today.apm,
                    apl=today.apl,
                    apm_trending=Trending.KEEP,
                ),
                historical=InfoData(
                    pps=history.pps,
                    lpm=history.lpm,
                    lpm_trending=Trending.KEEP,
                    apm=history.apm,
                    apl=history.apl,
                    apm_trending=Trending.KEEP,
                ),
                lang=get_lang(),
            ),
        )
    ) as page_hash:
        return await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html')


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
        total = get_avg_metrics(profile.total)
        message += '\n历史统计数据为: '
        message += f"\nL'PM: {total.lpm} ( {total.pps} pps )"
        message += f'\nAPM: {total.apm} ( x{total.apl} )'
    else:
        message += '\n暂无历史统计数据'
    return UniMessage(message)


async def make_query_result(profile: UserProfile) -> UniMessage:
    try:
        return UniMessage.image(raw=await make_query_image(profile))
    except FallbackError:
        ...
    return make_query_text(profile)
