from asyncio import gather
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from hashlib import md5
from math import ceil, floor
from typing import ClassVar, TypeVar, overload
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from aiofiles import open
from nonebot import get_driver
from nonebot.adapters import Event
from nonebot.compat import type_validate_json
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_apscheduler import scheduler  # type: ignore[import-untyped]
from nonebot_plugin_localstore import get_data_file  # type: ignore[import-untyped]
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from nonebot_plugin_user import User as NBUser  # type: ignore[import-untyped]
from nonebot_plugin_user import get_user  # type: ignore[import-untyped]
from sqlalchemy import select
from zstandard import ZstdDecompressor

from ...db import query_bind_info, trigger
from ...utils.exception import FallbackError
from ...utils.host import HostPage, get_self_netloc
from ...utils.metrics import TetrisMetricsProWithPPSVS, get_metrics
from ...utils.render import render
from ...utils.render.schemas.base import Avatar, Ranking
from ...utils.render.schemas.tetrio.tetrio_info import Info as V1TemplateInfo
from ...utils.render.schemas.tetrio.tetrio_info import Radar, TetraLeague, TetraLeagueHistory, TetraLeagueHistoryData
from ...utils.render.schemas.tetrio.tetrio_info import User as V1TemplateUser
from ...utils.render.schemas.tetrio.tetrio_user_info_v2 import Badge, Blitz, Sprint, Statistic, TetraLeagueStatistic
from ...utils.render.schemas.tetrio.tetrio_user_info_v2 import Info as V2TemplateInfo
from ...utils.render.schemas.tetrio.tetrio_user_info_v2 import TetraLeague as V2TemplateTetraLeague
from ...utils.render.schemas.tetrio.tetrio_user_info_v2 import User as V2TemplateUser
from ...utils.screenshot import screenshot
from ...utils.typing import Me, Number
from ..constant import CANT_VERIFY_MESSAGE
from . import alc
from .api import Player, User, UserInfoSuccess
from .api.models import TETRIOHistoricalData
from .api.schemas.tetra_league import TetraLeagueSuccess
from .api.schemas.user_info import NeverPlayedLeague, NeverRatedLeague, RatedLeague
from .constant import GAME_TYPE, TR_MAX, TR_MIN
from .models import IORank, TETRIOUserConfig
from .typing import Template

UTC = timezone.utc

driver = get_driver()


@alc.assign('TETRIO.query')
async def _(  # noqa: PLR0913
    user: NBUser,
    event: Event,
    matcher: Matcher,
    target: At | Me,
    event_session: EventSession,
    template: Template | None = None,
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
            if template is None:
                template = await session.scalar(
                    select(TETRIOUserConfig.query_template).where(TETRIOUserConfig.id == user.id)
                )
        if bind is None:
            await matcher.finish('未查询到绑定信息')
        message = UniMessage(CANT_VERIFY_MESSAGE)
        player = Player(user_id=bind.game_account, trust=True)
        await (message + (await make_query_result(player, template or 'v1'))).finish()


@alc.assign('TETRIO.query')
async def _(user: NBUser, account: Player, event_session: EventSession, template: Template | None = None):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[],
    ):
        async with get_session() as session:
            if template is None:
                template = await session.scalar(
                    select(TETRIOUserConfig.query_template).where(TETRIOUserConfig.id == user.id)
                )
        await (await make_query_result(account, template or 'v1')).finish()


def get_value_bounds(values: list[int | float]) -> tuple[int, int]:
    value_max = 10 * ceil(max(values) / 10)
    value_min = 10 * floor(min(values) / 10)
    return value_max, value_min


def get_split(value_max: int, value_min: int) -> tuple[int, int]:
    offset = 0
    overflow = 0

    while True:
        if (new_max_value := value_max + offset + overflow) > TR_MAX:
            overflow -= 1
            continue
        if (new_min_value := value_min - offset + overflow) < TR_MIN:
            overflow += 1
            continue
        if ((new_max_value - new_min_value) / 40).is_integer():
            split_value = int((value_max + offset - (value_min - offset)) / 4)
            break
        offset += 1
    return split_value, offset + overflow


def get_specified_point(
    previous_point: TetraLeagueHistoryData,
    behind_point: TetraLeagueHistoryData,
    point_time: datetime,
) -> TetraLeagueHistoryData:
    """根据给出的 previous_point 和 behind_point, 推算 point_time 点处的数据

    Args:
        previous_point (Data): 前面的数据点
        behind_point (Data): 后面的数据点
        point_time (datetime): 要推算的点的位置

    Returns:
        Data: 要推算的点的数据
    """
    # 求两个点的斜率
    slope = (behind_point.tr - previous_point.tr) / (
        datetime.timestamp(behind_point.record_at) - datetime.timestamp(previous_point.record_at)
    )
    return TetraLeagueHistoryData(
        record_at=point_time,
        tr=previous_point.tr + slope * (datetime.timestamp(point_time) - datetime.timestamp(previous_point.record_at)),
    )


async def query_historical_data(user: User, user_info: UserInfoSuccess) -> list[TetraLeagueHistoryData]:
    today = datetime.now(ZoneInfo('Asia/Shanghai')).replace(hour=0, minute=0, second=0, microsecond=0)
    forward = timedelta(days=9)
    start_time = (today - forward).astimezone(UTC)
    async with get_session() as session:
        historical_data = (
            await session.scalars(
                select(TETRIOHistoricalData)
                .where(TETRIOHistoricalData.update_time >= start_time)
                .where(TETRIOHistoricalData.user_unique_identifier == user.unique_identifier)
                .where(TETRIOHistoricalData.api_type == 'User Info')
            )
        ).all()
        if historical_data:
            extra = (
                await session.scalars(
                    select(TETRIOHistoricalData)
                    .where(TETRIOHistoricalData.user_unique_identifier == user.unique_identifier)
                    .where(TETRIOHistoricalData.api_type == 'User Info')
                    .order_by(TETRIOHistoricalData.id.desc())
                    .where(TETRIOHistoricalData.id < min([i.id for i in historical_data]))
                    .limit(1)
                )
            ).one_or_none()
            if extra is not None:
                historical_data = list(historical_data)
                historical_data.append(extra)
    full_export_data = FullExport.get_data(user.unique_identifier)
    if not historical_data and not full_export_data:
        return [
            TetraLeagueHistoryData(record_at=today - forward, tr=user_info.data.user.league.rating),
            TetraLeagueHistoryData(record_at=today.replace(microsecond=1000), tr=user_info.data.user.league.rating),
        ]
    histories = [
        TetraLeagueHistoryData(
            record_at=i.update_time.astimezone(ZoneInfo('Asia/Shanghai')),
            tr=i.data.data.user.league.rating,
        )
        for i in historical_data
        if isinstance(i.data, UserInfoSuccess) and isinstance(i.data.data.user.league, RatedLeague)
    ] + full_export_data

    # 按照时间排序
    histories = sorted(histories, key=lambda x: x.record_at)
    for index, value in enumerate(histories):
        # 在历史记录里找有没有今天0点后的数据, 并且至少要有两个数据点
        if value.record_at > today and len(histories) >= 2:  # noqa: PLR2004
            histories = histories[:index] + [
                get_specified_point(histories[index - 1], histories[index], today.replace(microsecond=1000))
            ]
            break
    else:
        histories.append(
            get_specified_point(
                histories[-1],
                TetraLeagueHistoryData(record_at=user_info.cache.cached_at, tr=user_info.data.user.league.rating),
                today.replace(microsecond=1000),
            )
        )
    if histories[0].record_at < (today - forward):
        histories[0] = get_specified_point(
            histories[0],
            histories[1],
            today - forward,
        )
    else:
        histories.insert(0, TetraLeagueHistoryData(record_at=today - forward, tr=histories[0].tr))
    return histories


L = TypeVar('L', NeverPlayedLeague, NeverRatedLeague, RatedLeague)


@overload
def get_league(user_info: UserInfoSuccess, league_type: type[L]) -> L: ...
@overload
def get_league(
    user_info: UserInfoSuccess, league_type: None = None
) -> NeverPlayedLeague | NeverRatedLeague | RatedLeague: ...
def get_league(
    user_info: UserInfoSuccess, league_type: type[L] | None = None
) -> L | NeverPlayedLeague | NeverRatedLeague | RatedLeague:
    league = user_info.data.user.league
    if league_type is None:
        return league
    if isinstance(league, league_type):
        return league
    raise FallbackError


async def make_query_image_v1(player: Player) -> bytes:
    user, user_info, sprint, blitz = await gather(player.user, player.get_info(), player.sprint, player.blitz)
    league = get_league(user_info, RatedLeague)
    if league.vs is None:
        raise FallbackError
    histories = await query_historical_data(user, user_info)
    value_max, value_min = get_value_bounds([i.tr for i in histories])
    split_value, offset = get_split(value_max, value_min)
    if sprint.record is not None:
        duration = timedelta(milliseconds=sprint.record.endcontext.final_time).total_seconds()
        sprint_value = f'{duration:.3f}s' if duration < 60 else f'{duration // 60:.0f}m {duration % 60:.3f}s'  # noqa: PLR2004
    else:
        sprint_value = 'N/A'
    blitz_value = f'{blitz.record.endcontext.score:,}' if blitz.record is not None else 'N/A'
    netloc = get_self_netloc()
    async with HostPage(
        page=await render(
            'v1/tetrio/info',
            V1TemplateInfo(
                user=V1TemplateUser(
                    avatar=f'http://{netloc}/host/resource/tetrio/avatars/{user.ID}?{urlencode({"revision": user_info.data.user.avatar_revision})}'
                    if user_info.data.user.avatar_revision is not None and user_info.data.user.avatar_revision != 0
                    else Avatar(
                        type='identicon',
                        hash=md5(user_info.data.user.id.encode()).hexdigest(),  # noqa: S324
                    ),
                    name=user.name.upper(),
                    bio=user_info.data.user.bio,
                ),
                ranking=Ranking(
                    rating=round(league.glicko, 2),
                    rd=round(league.rd, 2),
                ),
                tetra_league=TetraLeague(
                    rank=league.rank,
                    tr=round(league.rating, 2),
                    global_rank=league.standing,
                    pps=league.pps,
                    lpm=round(lpm := (league.pps * 24), 2),
                    apm=league.apm,
                    apl=round(league.apm / lpm, 2),
                    vs=league.vs,
                    adpm=round(adpm := (league.vs * 0.6), 2),
                    adpl=round(adpm / lpm, 2),
                ),
                tetra_league_history=TetraLeagueHistory(
                    data=histories,
                    split_interval=split_value,
                    min_tr=value_min,
                    max_tr=value_max,
                    offset=offset,
                ),
                radar=Radar(
                    app=(app := (league.apm / (60 * league.pps))),
                    dsps=(dsps := ((league.vs / 100) - (league.apm / 60))),
                    dspp=(dspp := (dsps / league.pps)),
                    ci=150 * dspp - 125 * app + 50 * (league.vs / league.apm) - 25,
                    ge=2 * ((app * dsps) / league.pps),
                ),
                sprint=sprint_value,
                blitz=blitz_value,
            ),
        )
    ) as page_hash:
        return await screenshot(f'http://{netloc}/host/{page_hash}.html')


N = TypeVar('N', int, float)


def handling_special_value(value: N) -> N | None:
    return value if value != -1 else None


async def make_query_image_v2(player: Player) -> bytes:
    user, user_info, sprint, blitz, zen = await gather(
        player.user, player.get_info(), player.sprint, player.blitz, player.zen
    )
    league = get_league(user_info)
    histories = await query_historical_data(user, user_info)

    if sprint.record is not None:
        duration = timedelta(milliseconds=sprint.record.endcontext.final_time).total_seconds()
        sprint_value = f'{duration:.3f}s' if duration < 60 else f'{duration // 60:.0f}m {duration % 60:.3f}s'  # noqa: PLR2004
    else:
        sprint_value = 'N/A'

    play_time: str | None
    if (game_time := handling_special_value(user_info.data.user.gametime)) is not None:
        if game_time // 3600 > 0:
            play_time = f'{game_time//3600:.0f}h {game_time % 3600 // 60:.0f}m {game_time % 60:.0f}s'
        elif game_time // 60 > 0:
            play_time = f'{game_time//60:.0f}m {game_time % 60:.0f}s'
        else:
            play_time = f'{game_time:.0f}s'
    else:
        play_time = game_time
    netloc = get_self_netloc()
    async with HostPage(
        await render(
            'v2/tetrio/user/info',
            V2TemplateInfo(
                user=V2TemplateUser(
                    id=user.ID,
                    name=user.name.upper(),
                    bio=user_info.data.user.bio,
                    banner=f'http://{netloc}/host/resource/tetrio/banners/{user.ID}?{urlencode({"revision": user_info.data.user.banner_revision})}'
                    if user_info.data.user.banner_revision is not None and user_info.data.user.banner_revision != 0
                    else None,
                    avatar=f'http://{netloc}/host/resource/tetrio/avatars/{user.ID}?{urlencode({"revision": user_info.data.user.avatar_revision})}'
                    if user_info.data.user.avatar_revision is not None and user_info.data.user.avatar_revision != 0
                    else Avatar(
                        type='identicon',
                        hash=md5(user_info.data.user.id.encode()).hexdigest(),  # noqa: S324
                    ),
                    badges=[
                        Badge(
                            id=i.id,
                            description=i.label,
                            group=i.group,
                            receive_at=i.ts if isinstance(i.ts, datetime) else None,
                        )
                        for i in user_info.data.user.badges
                    ],
                    country=user_info.data.user.country,
                    xp=user_info.data.user.xp,
                    friend_count=user_info.data.user.friend_count or 0,
                    supporter_tier=user_info.data.user.supporter_tier,
                    bad_standing=user_info.data.user.badstanding or False,
                    verified=user_info.data.user.verified,
                    playtime=play_time,
                    join_at=user_info.data.user.ts,
                ),
                tetra_league=V2TemplateTetraLeague(
                    rank=league.rank,
                    highest_rank=league.bestrank,
                    tr=round(league.rating, 2),
                    glicko=round(league.glicko, 2),
                    rd=round(league.rd, 2),
                    global_rank=handling_special_value(league.standing),
                    country_rank=handling_special_value(league.standing_local),
                    pps=(
                        metrics := get_metrics(pps=league.pps, apm=league.apm, vs=league.vs)
                        if league.vs is not None
                        else get_metrics(pps=league.pps, apm=league.apm)
                    ).pps,
                    apm=metrics.apm,
                    apl=metrics.apl,
                    vs=metrics.vs if isinstance(metrics, TetrisMetricsProWithPPSVS) else None,
                    adpl=metrics.adpl if isinstance(metrics, TetrisMetricsProWithPPSVS) else None,
                    statistic=TetraLeagueStatistic(
                        total=league.gamesplayed,
                        wins=league.gameswon,
                    ),
                    decaying=league.decaying,
                    history=histories,
                )
                if isinstance(league, RatedLeague)
                else None,
                statistic=Statistic(
                    total=handling_special_value(user_info.data.user.gamesplayed),
                    wins=handling_special_value(user_info.data.user.gameswon),
                ),
                sprint=Sprint(
                    time=sprint_value,
                    global_rank=sprint.rank,
                    play_at=sprint.record.ts,
                )
                if sprint.record is not None
                else None,
                blitz=Blitz(
                    score=blitz.record.endcontext.score,
                    global_rank=blitz.rank,
                    play_at=blitz.record.ts,
                )
                if blitz.record is not None
                else None,
                zen=zen,
            ),
        ),
    ) as page_hash:
        return await screenshot(f'http://{netloc}/host/{page_hash}.html')


async def make_query_text(player: Player) -> UniMessage:
    user, user_info, sprint, blitz = await gather(player.user, player.get_info(), player.sprint, player.blitz)
    league = get_league(user_info)

    user_name = user.name.upper()

    message = ''
    if isinstance(league, NeverPlayedLeague):
        message += f'用户 {user_name} 没有排位统计数据'
    else:
        if isinstance(league, NeverRatedLeague):
            message += f'用户 {user_name} 暂未完成定级赛, 最近十场的数据:'
        else:
            if league.rank == 'z':
                message += f'用户 {user_name} 暂无段位, {round(league.rating,2)} TR'
            else:
                message += f'{league.rank.upper()} 段用户 {user_name} {round(league.rating,2)} TR (#{league.standing})'
            message += f', 段位分 {round(league.glicko,2)}±{round(league.rd,2)}, 最近十场的数据:'
        metrics = (
            get_metrics(pps=league.pps, apm=league.apm, vs=league.vs)
            if league.vs is not None
            else get_metrics(pps=league.pps, apm=league.apm)
        )
        message += f"\nL'PM: {metrics.lpm} ( {metrics.pps} pps )"
        message += f'\nAPM: {metrics.apm} ( x{metrics.apl} )'
        if isinstance(metrics, TetrisMetricsProWithPPSVS):
            message += f'\nADPM: {metrics.adpm} ( x{metrics.adpl} ) ( {metrics.vs}vs )'
    if sprint.record is not None:
        message += f'\n40L: {round(sprint.record.endcontext.final_time/1000,2)}s'
        message += f' ( #{sprint.rank} )' if sprint.rank is not None else ''
    if blitz.record is not None:
        message += f'\nBlitz: {blitz.record.endcontext.score}'
        message += f' ( #{blitz.rank} )' if blitz.rank is not None else ''
    return UniMessage(message)


async def make_query_result(player: Player, template: Template) -> UniMessage:
    try:
        if template == 'v1':
            return UniMessage.image(raw=await make_query_image_v1(player))
        if template == 'v2':
            return UniMessage.image(raw=await make_query_image_v2(player))
    except FallbackError:
        ...
    return await make_query_text(player)


class FullExport:
    cache: ClassVar[defaultdict[str, set[tuple[datetime, Number]]]] = defaultdict(set)
    latest_update: ClassVar[date | None] = None

    @classmethod
    async def init(cls) -> None:
        async with get_session() as session:
            full_exports = (await session.scalars(select(IORank).where(IORank.update_time >= cls.start_time()))).all()
        await gather(
            *[
                cls._load(update_time, file_hash)
                for file_hash, update_time in {
                    i.file_hash: i.update_time for i in full_exports if i.file_hash is not None
                }.items()
            ]
        )

    @classmethod
    async def update(cls) -> None:
        if cls.latest_update == datetime.now(tz=ZoneInfo('Asia/Shanghai')).date():
            return
        start_time = cls.start_time()
        for i in cls.cache:
            cls.cache[i] = {j for j in cls.cache[i] if j[0] >= start_time}
        latest_time = max(cls.cache)
        async with get_session() as session:
            full_exports = (await session.scalars(select(IORank).where(IORank.update_time > latest_time))).all()
        await gather(
            *[
                cls._load(update_time, file_hash)
                for file_hash, update_time in {
                    i.file_hash: i.update_time for i in full_exports if i.file_hash is not None
                }.items()
            ]
        )
        cls.latest_update = datetime.now(tz=ZoneInfo('Asia/Shanghai')).date()

    @classmethod
    def get_data(cls, unique_identifier: str) -> list[TetraLeagueHistoryData]:
        return [TetraLeagueHistoryData(record_at=i[0], tr=i[1]) for i in cls.cache[unique_identifier]]

    @classmethod
    def start_time(cls) -> datetime:
        return (
            datetime.now(ZoneInfo('Asia/Shanghai')).replace(hour=0, minute=0, second=0, microsecond=0)
            - timedelta(days=9)
        ).astimezone(UTC)

    @classmethod
    async def _load(cls, update_time: datetime, file_hash: str) -> None:
        try:
            users = type_validate_json(TetraLeagueSuccess, await cls.decompress(file_hash)).data.users
        except FileNotFoundError:
            await cls.clear_invalid(file_hash)
            return
        update_time = update_time.astimezone(ZoneInfo('Asia/Shanghai'))
        for i in users:
            cls.cache[i.id].add((update_time, i.league.rating))

    @classmethod
    async def decompress(cls, file_hash: str) -> bytes:
        async with open(get_data_file('nonebot_plugin_tetris_stats', f'{file_hash}.json.zst'), mode='rb') as file:
            return ZstdDecompressor().decompress(await file.read())

    @classmethod
    async def clear_invalid(cls, file_hash: str) -> None:
        async with get_session() as session:
            full_exports = (await session.scalars(select(IORank).where(IORank.file_hash == file_hash))).all()
            for i in full_exports:
                i.file_hash = None
            await session.commit()


@driver.on_startup
async def _():
    await FullExport.init()
    scheduler.add_job(FullExport.update, 'interval', hours=1)
