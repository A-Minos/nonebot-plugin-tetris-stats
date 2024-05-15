import contextlib
from asyncio import gather
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from hashlib import md5
from math import ceil, floor
from typing import ClassVar
from urllib.parse import urlunparse
from zoneinfo import ZoneInfo

from aiofiles import open
from nonebot import get_driver
from nonebot.adapters import Bot, Event
from nonebot.compat import type_validate_json
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import At
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_apscheduler import scheduler  # type: ignore[import-untyped]
from nonebot_plugin_localstore import get_data_file  # type: ignore[import-untyped]
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from sqlalchemy import select
from zstandard import ZstdDecompressor

from ...db import query_bind_info, trigger
from ...utils.host import HostPage, get_self_netloc
from ...utils.platform import get_platform
from ...utils.render import TETRIOInfo, render
from ...utils.render.schemas.base import Avatar
from ...utils.render.schemas.tetrio_info import Data, Radar, Ranking, TetraLeague, TetraLeagueHistory
from ...utils.render.schemas.tetrio_info import User as TemplateUser
from ...utils.screenshot import screenshot
from ...utils.typing import Me, Number
from ..constant import CANT_VERIFY_MESSAGE
from . import alc
from .api import Player, User, UserInfoSuccess
from .api.models import TETRIOHistoricalData
from .api.schemas.tetra_league import TetraLeagueSuccess
from .api.schemas.user_info import NeverPlayedLeague, NeverRatedLeague, RatedLeague
from .api.schemas.user_records import SoloModeRecord, SoloRecord
from .constant import GAME_TYPE, TR_MAX, TR_MIN
from .model import IORank

UTC = timezone.utc

driver = get_driver()


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
        message = UniMessage(CANT_VERIFY_MESSAGE)
        player = Player(user_id=bind.game_account, trust=True)
        user, user_info, user_records = await gather(player.user, player.get_info(), player.get_records())
        sprint = user_records.data.records.sprint
        blitz = user_records.data.records.blitz
        with contextlib.suppress(TypeError):
            message += UniMessage.image(raw=await make_query_image(user, user_info, sprint.record, blitz.record))
            await message.finish()
        message += make_query_text(user_info, sprint, blitz)
        await message.finish()


@alc.assign('query')
async def _(account: Player, event_session: EventSession):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[],
    ):
        user, user_info, user_records = await gather(account.user, account.get_info(), account.get_records())
        sprint = user_records.data.records.sprint
        blitz = user_records.data.records.blitz
        with contextlib.suppress(TypeError):
            await UniMessage.image(raw=await make_query_image(user, user_info, sprint.record, blitz.record)).finish()
        await make_query_text(user_info, sprint, blitz).finish()


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
    previous_point: Data,
    behind_point: Data,
    point_time: datetime,
) -> Data:
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
    return Data(
        record_at=point_time,
        tr=previous_point.tr + slope * (datetime.timestamp(point_time) - datetime.timestamp(previous_point.record_at)),
    )


async def query_historical_data(user: User, user_info: UserInfoSuccess) -> list[Data]:
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
            Data(record_at=today - forward, tr=user_info.data.user.league.rating),
            Data(record_at=today.replace(microsecond=1000), tr=user_info.data.user.league.rating),
        ]
    histories = [
        Data(
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
                Data(record_at=user_info.cache.cached_at, tr=user_info.data.user.league.rating),
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
        histories.insert(0, Data(record_at=today - forward, tr=histories[0].tr))
    return histories


async def make_query_image(
    user: User, user_info: UserInfoSuccess, sprint: SoloRecord | None, blitz: SoloRecord | None
) -> bytes:
    league = user_info.data.user.league
    if not isinstance(league, RatedLeague) or league.vs is None:
        raise TypeError
    user_name = user_info.data.user.username.upper()
    histories = await query_historical_data(user, user_info)
    value_max, value_min = get_value_bounds([i.tr for i in histories])
    split_value, offset = get_split(value_max, value_min)
    if sprint is not None:
        duration = timedelta(milliseconds=sprint.endcontext.final_time).total_seconds()
        sprint_value = f'{duration:.1f}s' if duration < 60 else f'{duration // 60:.0f}m {duration % 60:.1f}s'  # noqa: PLR2004
    else:
        sprint_value = 'N/A'
    blitz_value = f'{blitz.endcontext.score:,}' if blitz is not None else 'N/A'
    async with HostPage(
        await render(
            'tetrio/info',
            TETRIOInfo(
                user=TemplateUser(
                    avatar=f'https://tetr.io/user-content/avatars/{user_info.data.user.id}.jpg?rv={user_info.data.user.avatar_revision}'
                    if user_info.data.user.avatar_revision is not None
                    else Avatar(
                        type='identicon',
                        hash=md5(user_info.data.user.id.encode()).hexdigest(),  # noqa: S324
                    ),
                    name=user_name,
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
        return await screenshot(urlunparse(('http', get_self_netloc(), f'/host/{page_hash}.html', '', '', '')))


def make_query_text(user_info: UserInfoSuccess, sprint: SoloModeRecord, blitz: SoloModeRecord) -> UniMessage:
    league = user_info.data.user.league
    user_name = user_info.data.user.username.upper()
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
        lpm = league.pps * 24
        message += f"\nL'PM: {round(lpm, 2)} ( {league.pps} pps )"
        message += f'\nAPM: {league.apm} ( x{round(league.apm/lpm,2)} )'
        if league.vs is not None:
            adpm = league.vs * 0.6
            message += f'\nADPM: {round(adpm,2)} ( x{round(adpm/lpm,2)} ) ( {league.vs}vs )'
    if sprint.record is not None:
        message += f'\n40L: {round(sprint.record.endcontext.final_time/1000,2)}s'
        message += f' ( #{sprint.rank} )' if sprint.rank is not None else ''
    if blitz.record is not None:
        message += f'\nBlitz: {blitz.record.endcontext.score}'
        message += f' ( #{blitz.rank} )' if blitz.rank is not None else ''
    return UniMessage(message)


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
    def get_data(cls, unique_identifier: str) -> list[Data]:
        return [Data(record_at=i[0], tr=i[1]) for i in cls.cache[unique_identifier]]

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
