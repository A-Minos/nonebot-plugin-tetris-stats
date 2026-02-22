from datetime import datetime, timedelta, timezone

from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At
from nonebot_plugin_alconna.uniseg import Image, UniMessage
from nonebot_plugin_orm import AsyncSession, get_session
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_uninfo.orm import get_session_persist_id
from nonebot_plugin_user import User as NBUser
from nonebot_plugin_user import get_user
from sqlalchemy import select

from ...db import query_bind_info, resolve_compare_delta, trigger
from ...i18n import Lang
from ...utils.exception import FallbackError
from ...utils.lang import get_lang
from ...utils.metrics import TetrisMetricsBasicWithLPM, get_metrics
from ...utils.render import render_image
from ...utils.render.avatar import get_avatar
from ...utils.render.schemas.base import People, Trending
from ...utils.render.schemas.v1.top.info import Data as InfoData
from ...utils.render.schemas.v1.top.info import Info
from ...utils.typedefs import Me
from . import alc
from .api import Player
from .api.models import TOPHistoricalData
from .api.schemas.user_profile import Data, UserProfile
from .constant import GAME_TYPE
from .models import TOPUserConfig

UTC = timezone.utc


async def get_compare_profile(session: AsyncSession, user_name: str, target_time: datetime) -> UserProfile | None:
    before = await session.scalar(
        select(TOPHistoricalData)
        .where(
            TOPHistoricalData.user_unique_identifier == user_name,
            TOPHistoricalData.api_type == 'User Profile',
            TOPHistoricalData.update_time <= target_time,
        )
        .order_by(TOPHistoricalData.update_time.desc())
        .limit(1)
    )
    after = await session.scalar(
        select(TOPHistoricalData)
        .where(
            TOPHistoricalData.user_unique_identifier == user_name,
            TOPHistoricalData.api_type == 'User Profile',
            TOPHistoricalData.update_time >= target_time,
        )
        .order_by(TOPHistoricalData.update_time.asc())
        .limit(1)
    )
    if before is None:
        selected = after
    elif after is None:
        selected = before
    else:
        selected = (
            before
            if abs((target_time - before.update_time).total_seconds())
            <= abs((target_time - after.update_time).total_seconds())
            else after
        )
    if selected is None or not isinstance(selected.data, UserProfile):
        return None
    return selected.data


def compare_metrics(
    current: TetrisMetricsBasicWithLPM, compare: TetrisMetricsBasicWithLPM | None
) -> tuple[Trending, Trending]:
    if compare is None:
        return Trending.KEEP, Trending.KEEP
    return Trending.compare(compare.lpm, current.lpm), Trending.compare(compare.apm, current.apm)


@alc.assign('TOP.query')
async def _(  # noqa: PLR0913
    user: NBUser,
    event: Event,
    matcher: Matcher,
    target: At | Me,
    event_session: Uninfo,
    compare: timedelta | None = None,
):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[f'--compare {compare}'] if compare is not None else [],
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
            compare_delta = await resolve_compare_delta(TOPUserConfig, session, user.id, compare)
            player = Player(user_name=bind.game_account, trust=True)
            profile = await player.get_profile()
            compare_profile = await get_compare_profile(
                session,
                profile.user_name,
                datetime.now(tz=UTC) - compare_delta,
            )
        await (
            UniMessage.i18n(Lang.interaction.warning.unverified)
            + (
                UniMessage('\n')
                if not (result := await make_query_result(profile, compare_profile)).has(Image)
                else UniMessage()
            )
            + result
        ).finish()


@alc.assign('TOP.query')
async def _(user: NBUser, account: Player, event_session: Uninfo, compare: timedelta | None = None):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[f'--compare {compare}'] if compare is not None else [],
    ):
        async with get_session() as session:
            compare_delta = await resolve_compare_delta(TOPUserConfig, session, user.id, compare)
            profile = await account.get_profile()
            compare_profile = await get_compare_profile(
                session,
                profile.user_name,
                datetime.now(tz=UTC) - compare_delta,
            )
        await (await make_query_result(profile, compare_profile)).finish()


def get_avg_metrics(data: list[Data]) -> TetrisMetricsBasicWithLPM:
    total_lpm = total_apm = 0.0
    for value in data:
        total_lpm += value.lpm
        total_apm += value.apm
    num = len(data)
    return get_metrics(lpm=total_lpm / num, apm=total_apm / num)


async def make_query_image(profile: UserProfile, compare: UserProfile | None) -> bytes:
    if profile.today is None or profile.total is None:
        raise FallbackError
    today = get_metrics(lpm=profile.today.lpm, apm=profile.today.apm)
    history = get_avg_metrics(profile.total)
    compare_today = get_metrics(lpm=compare.today.lpm, apm=compare.today.apm) if compare and compare.today else None
    compare_history = get_avg_metrics(compare.total) if compare is not None and compare.total is not None else None
    today_lpm_trending, today_apm_trending = compare_metrics(today, compare_today)
    history_lpm_trending, history_apm_trending = compare_metrics(history, compare_history)
    return await render_image(
        Info(
            user=People(avatar=get_avatar(profile.user_name), name=profile.user_name),
            today=InfoData(
                pps=today.pps,
                lpm=today.lpm,
                lpm_trending=today_lpm_trending,
                apm=today.apm,
                apl=today.apl,
                apm_trending=today_apm_trending,
            ),
            historical=InfoData(
                pps=history.pps,
                lpm=history.lpm,
                lpm_trending=history_lpm_trending,
                apm=history.apm,
                apl=history.apl,
                apm_trending=history_apm_trending,
            ),
            lang=get_lang(),
        ),
    )


def make_query_text(profile: UserProfile) -> UniMessage:
    message = ''
    if profile.today is not None:
        today = get_metrics(lpm=profile.today.lpm, apm=profile.today.apm)
        message += Lang.stats.daily_stats(name=profile.user_name)
        message += Lang.stats.lpm(lpm=today.lpm, pps=today.pps)
        message += Lang.stats.apm(apm=today.apm, apl=today.apl)
    else:
        message += Lang.stats.no_daily(name=profile.user_name)
    if profile.total is not None:
        total = get_avg_metrics(profile.total)
        message += Lang.stats.history_stats()
        message += Lang.stats.lpm(lpm=total.lpm, pps=total.pps)
        message += Lang.stats.apm(apm=total.apm, apl=total.apl)
    else:
        message += Lang.stats.no_history()
    return UniMessage(message)


async def make_query_result(profile: UserProfile, compare: UserProfile | None) -> UniMessage:
    try:
        return UniMessage.image(raw=await make_query_image(profile, compare))
    except FallbackError:
        ...
    return make_query_text(profile)
