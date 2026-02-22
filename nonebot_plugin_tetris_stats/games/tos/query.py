from asyncio import gather
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Literal, NamedTuple
from zoneinfo import ZoneInfo

from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At
from nonebot_plugin_alconna.uniseg import Image, UniMessage
from nonebot_plugin_orm import AsyncSession, get_session
from nonebot_plugin_uninfo import Uninfo, User
from nonebot_plugin_uninfo.orm import get_session_persist_id
from nonebot_plugin_user import User as NBUser
from nonebot_plugin_user import get_user
from sqlalchemy import select

from ...db import query_bind_info, resolve_compare_delta, trigger
from ...i18n import Lang
from ...utils.chart import get_split, get_value_bounds, handle_history_data
from ...utils.exception import FallbackError, RequestError
from ...utils.image import get_avatar
from ...utils.lang import get_lang
from ...utils.metrics import TetrisMetricsProWithLPMADPM, get_metrics
from ...utils.render import render_image
from ...utils.render.avatar import get_avatar as get_random_avatar
from ...utils.render.schemas.base import HistoryData, People, Trending
from ...utils.render.schemas.v1.base import History
from ...utils.render.schemas.v1.tos.info import Info, Multiplayer, Singleplayer
from ...utils.time_it import time_it
from ...utils.typedefs import Me, Number
from . import alc
from .api import Player
from .api.models import TOSHistoricalData
from .api.schemas.user_info import UserInfoSuccess
from .api.schemas.user_profile import Data as UserProfileData
from .api.schemas.user_profile import UserProfile
from .constant import GAME_TYPE
from .models import TOSUserConfig

UTC = timezone.utc


def add_special_handlers(
    teaid_prefix: Literal['onebot-', 'kook-', 'discord-', 'qqguild-'], match_event: type[Event]
) -> None:
    @alc.assign('TOS.query')
    async def _(
        user: NBUser,
        event: Event,
        target: At | Me,
        event_session: Uninfo,
        compare: timedelta | None = None,
    ):
        if isinstance(event, match_event):
            async with trigger(
                session_persist_id=await get_session_persist_id(event_session),
                game_platform=GAME_TYPE,
                command_type='query',
                command_args=[f'--compare {compare}'] if compare is not None else [],
            ):
                player = Player(
                    teaid=f'{teaid_prefix}{target.target}'
                    if isinstance(target, At)
                    else f'{teaid_prefix}{event.get_user_id()}',
                    trust=True,
                )
                try:
                    async with get_session() as session:
                        await (
                            await make_query_result(
                                player,
                                await resolve_compare_delta(TOSUserConfig, session, user.id, compare),
                                None if isinstance(target, At) else event_session.user,
                            )
                        ).finish()
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
async def _(  # noqa: PLR0913
    user: NBUser,
    event: Event,
    matcher: Matcher,
    target: At | Me,
    event_session: Uninfo,
    compare: timedelta | None = None,
):
    async with (
        trigger(
            session_persist_id=await get_session_persist_id(event_session),
            game_platform=GAME_TYPE,
            command_type='query',
            command_args=[f'--compare {compare}'] if compare is not None else [],
        ),
        get_session() as session,
    ):
        bind = await query_bind_info(
            session=session,
            user=await get_user(event_session.scope, target.target if isinstance(target, At) else event.get_user_id()),
            game_platform=GAME_TYPE,
        )
        if bind is None:
            await matcher.finish(Lang.bind.not_found())
        player = Player(teaid=bind.game_account, trust=True)
        await (
            UniMessage.i18n(Lang.interaction.warning.unverified)
            + (
                UniMessage('\n')
                if not (
                    result := await make_query_result(
                        player,
                        await resolve_compare_delta(TOSUserConfig, session, user.id, compare),
                        None if isinstance(target, At) else event_session.user,
                    )
                ).has(Image)
                else UniMessage()
            )
            + result
        ).finish()


@alc.assign('TOS.query')
async def _(user: NBUser, account: Player, event_session: Uninfo, compare: timedelta | None = None):
    async with (
        trigger(
            session_persist_id=await get_session_persist_id(event_session),
            game_platform=GAME_TYPE,
            command_type='query',
            command_args=[f'--compare {compare}'] if compare is not None else [],
        ),
        get_session() as session,
    ):
        await (
            await make_query_result(
                account,
                await resolve_compare_delta(TOSUserConfig, session, user.id, compare),
                None,
            )
        ).finish()


class GameData(NamedTuple):
    game_num: int
    metrics: TetrisMetricsProWithLPMADPM
    or_: Number
    dspp: Number
    ge: Number


class GameAccumulator:
    def __init__(self, target_num: int) -> None:
        self._target_num = max(1, target_num)
        self._weighted_total_lpm = 0.0
        self._weighted_total_apm = 0.0
        self._weighted_total_adpm = 0.0
        self._total_time = 0.0
        self._total_attack = 0
        self._total_dig = 0
        self._total_offset = 0
        self._total_pieces = 0
        self._total_receive = 0
        self._num = 0

    @property
    def num(self) -> int:
        return self._num

    @property
    def reached_target(self) -> bool:
        return self._num >= self._target_num

    def add(self, data: UserProfileData) -> bool:
        # 排除单人局和时间为 0 的游戏
        # 茶: 不计算没挖掘的局, 即使 apm 和 lpm 也如此
        if data.num_players == 1 or data.time == 0:
            return False
        seconds = data.time / 1000
        self._weighted_total_lpm += 24 * data.pieces
        self._weighted_total_apm += 60 * data.attack
        self._weighted_total_adpm += 60 * (data.attack + data.dig)
        self._total_attack += data.attack
        self._total_dig += data.dig
        self._total_offset += data.offset
        self._total_pieces += data.pieces
        self._total_receive += data.receive
        self._total_time += seconds
        self._num += 1
        return True

    def to_game_data(self) -> GameData | None:
        if self._num == 0 or self._total_time == 0:
            return None
        metrics = get_metrics(
            lpm=self._weighted_total_lpm / self._total_time,
            apm=self._weighted_total_apm / self._total_time,
            adpm=self._weighted_total_adpm / self._total_time,
        )
        return GameData(
            game_num=self._num,
            metrics=metrics,
            or_=self._total_offset / self._total_receive * 100 if self._total_receive else 0.0,
            dspp=self._total_dig / self._total_pieces if self._total_pieces else 0.0,
            ge=2 * ((self._total_attack * self._total_dig) / self._total_pieces**2) if self._total_pieces else 0.0,
        )


def get_game_data_from_profile(profile: UserProfile, query_num: int = 50) -> GameData | None:
    accumulator = GameAccumulator(query_num)
    for row in profile.data:
        if accumulator.reached_target:
            break
        accumulator.add(row)
    return accumulator.to_game_data()


def get_game_data_from_profiles(profiles: Iterable[UserProfile], query_num: int = 50) -> GameData | None:
    accumulator = GameAccumulator(query_num)
    for profile in profiles:
        for row in profile.data:
            if accumulator.reached_target:
                return accumulator.to_game_data()
            accumulator.add(row)
    return accumulator.to_game_data()


async def get_game_data(player: Player, query_num: int = 50) -> GameData | None:
    """获取游戏数据"""
    user_profile = await player.get_profile()
    return get_game_data_from_profile(user_profile, query_num)


async def get_compare_profile(
    session: AsyncSession, unique_identifier: str, target_time: datetime
) -> UserProfile | None:
    before = await session.scalar(
        select(TOSHistoricalData)
        .where(
            TOSHistoricalData.user_unique_identifier == unique_identifier,
            TOSHistoricalData.api_type == 'User Profile',
            TOSHistoricalData.update_time <= target_time,
        )
        .order_by(TOSHistoricalData.update_time.desc())
        .limit(1)
    )
    after = await session.scalar(
        select(TOSHistoricalData)
        .where(
            TOSHistoricalData.user_unique_identifier == unique_identifier,
            TOSHistoricalData.api_type == 'User Profile',
            TOSHistoricalData.update_time >= target_time,
        )
        .order_by(TOSHistoricalData.update_time.asc())
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


@time_it
async def get_historical_data(unique_identifier: str) -> list[HistoryData]:
    async with get_session() as session:
        user_infos = (
            await session.scalars(
                select(TOSHistoricalData)
                .where(TOSHistoricalData.user_unique_identifier == unique_identifier)
                .where(TOSHistoricalData.api_type == 'User Info')
                .where(
                    TOSHistoricalData.update_time
                    > (
                        datetime.now(ZoneInfo('Asia/Shanghai')).replace(hour=0, minute=0, second=0, microsecond=0)
                        - timedelta(days=9)
                    ).replace(tzinfo=timezone.utc)
                )
                .order_by(TOSHistoricalData.id.asc())
            )
        ).all()
        if user_infos:
            extra_info = (
                await session.scalars(
                    select(TOSHistoricalData)
                    .where(TOSHistoricalData.id < user_infos[0].id)
                    .where(TOSHistoricalData.user_unique_identifier == unique_identifier)
                    .where(TOSHistoricalData.api_type == 'User Info')
                    .limit(1)
                )
            ).one_or_none()
            if extra_info is not None:
                user_infos = [extra_info, *user_infos]
    return [
        HistoryData(score=float(i.data.data.rating_now), record_at=i.update_time.astimezone(ZoneInfo('Asia/Shanghai')))
        for i in user_infos
        if isinstance(i.data, UserInfoSuccess)
    ]


class Trends(NamedTuple):
    lpm: Trending = Trending.KEEP
    apm: Trending = Trending.KEEP
    adpm: Trending = Trending.KEEP


async def get_trends(player: Player, compare_delta: timedelta) -> Trends:
    game_data = await get_game_data(player)
    if game_data is None:
        raise FallbackError
    async with get_session() as session:
        compare_profile = await get_compare_profile(
            session,
            (await player.user).teaid,
            datetime.now(tz=UTC) - compare_delta,
        )
        if compare_profile is None or (old_game_data := get_game_data_from_profile(compare_profile)) is None:
            raise FallbackError
    return Trends(
        lpm=Trending.compare(old_game_data.metrics.lpm, game_data.metrics.lpm),
        apm=Trending.compare(old_game_data.metrics.apm, game_data.metrics.apm),
        adpm=Trending.compare(old_game_data.metrics.adpm, game_data.metrics.adpm),
    )


async def make_query_image(
    player: Player,
    compare_delta: timedelta,
    event_user_info: User | None,
) -> bytes:
    user_info, game_data = await gather(player.get_info(), get_game_data(player))
    if game_data is None:
        raise FallbackError
    metrics = game_data.metrics
    trends = await get_trends(player, compare_delta)
    sprint_value = (
        (
            f'{duration:.3f}s'
            if (duration := timedelta(milliseconds=float(user_info.data.pb_sprint)).total_seconds()) < 60  # noqa: PLR2004
            else f'{duration // 60:.0f}m {duration % 60:.3f}s'
        )
        if user_info.data.pb_sprint != '2147483647'
        else 'N/A'
    )
    data = handle_history_data(await get_historical_data(user_info.data.teaid))
    values = get_value_bounds([i.score for i in data])
    return await render_image(
        Info(
            user=People(
                avatar=await get_avatar(event_user_info, 'Data URI', None)
                if event_user_info is not None
                else get_random_avatar(user_info.data.teaid),
                name=user_info.data.name,
            ),
            multiplayer=Multiplayer(
                history=History(
                    data=data,
                    max_value=values.value_max,
                    min_value=values.value_min,
                    split_interval=(split := get_split(value_bound=values, min_value=0)).split_value,
                    offset=split.offset,
                ),
                rating=round(float(user_info.data.rating_now), 2),
                rd=round(float(user_info.data.rd_now), 2),
                lpm=metrics.lpm,
                pps=metrics.pps,
                lpm_trending=trends.lpm,
                apm=metrics.apm,
                apl=metrics.apl,
                apm_trending=trends.apm,
                adpm=metrics.adpm,
                vs=metrics.vs,
                adpl=metrics.adpl,
                adpm_trending=trends.adpm,
                app=(app := (metrics.apm / (60 * metrics.pps))),
                or_=game_data.or_,
                dspp=game_data.dspp,
                ci=150 * game_data.dspp - 125 * app + 50 * (metrics.vs / metrics.apm) - 25,
                ge=game_data.ge,
            ),
            singleplayer=Singleplayer(
                sprint=sprint_value,
                challenge=f'{int(user_info.data.pb_challenge):,}' if user_info.data.pb_challenge != '0' else 'N/A',
                marathon=f'{int(user_info.data.pb_marathon):,}' if user_info.data.pb_marathon != '0' else 'N/A',
            ),
            lang=get_lang(),
        ),
    )


async def make_query_text(player: Player) -> UniMessage:
    user_info, game_data = await gather(player.get_info(), get_game_data(player))
    user_data = user_info.data
    message = Lang.stats.user_info(name=user_data.name, id=user_data.teaid)
    if user_data.ranked_games == '0':
        message += Lang.stats.no_rank()
    else:
        message += Lang.stats.rank_info(
            rating=round(float(user_data.rating_now), 2),
            rd=round(float(user_data.rd_now), 2),
            vol=round(float(user_data.vol_now), 2),
        )
    if game_data is None:
        message += Lang.stats.no_game()
    else:
        message += Lang.stats.recent_games(count=game_data.game_num)
        message += Lang.stats.lpm(lpm=game_data.metrics.lpm, pps=game_data.metrics.pps)
        message += Lang.stats.apm(apm=game_data.metrics.apm, apl=game_data.metrics.apl)
        message += Lang.stats.adpm(adpm=game_data.metrics.adpm, adpl=game_data.metrics.adpl, vs=game_data.metrics.vs)
    if user_data.pb_sprint != '2147483647':
        message += Lang.stats.sprint_pb(time=f'{float(user_data.pb_sprint) / 1000:.2f}')
    if user_data.pb_marathon != '0':
        message += Lang.stats.marathon_pb(score=user_data.pb_marathon)
    if user_data.pb_challenge != '0':
        message += Lang.stats.challenge_pb(score=user_data.pb_challenge)
    return UniMessage(message)


async def make_query_result(player: Player, compare_delta: timedelta, event_user_info: User | None) -> UniMessage:
    try:
        return UniMessage.image(raw=await make_query_image(player, compare_delta, event_user_info))
    except FallbackError:
        ...
    return await make_query_text(player)
