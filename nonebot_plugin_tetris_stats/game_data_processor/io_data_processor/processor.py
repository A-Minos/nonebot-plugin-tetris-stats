from asyncio import gather
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from hashlib import md5, sha512
from math import floor
from re import match
from statistics import mean
from typing import Literal
from urllib.parse import urlunparse

from aiofiles import open
from nonebot import get_driver
from nonebot.compat import type_validate_json
from nonebot.utils import run_sync
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_apscheduler import scheduler  # type: ignore[import-untyped]
from nonebot_plugin_localstore import get_data_file  # type: ignore[import-untyped]
from nonebot_plugin_orm import get_session
from nonebot_plugin_userinfo import UserInfo as NBUserInfo  # type: ignore[import-untyped]
from sqlalchemy import select
from typing_extensions import override
from zstandard import ZstdCompressor

from ...db import BindStatus, create_or_update_bind
from ...utils.avatar import get_avatar
from ...utils.exception import MessageFormatError, RequestError, WhatTheFuckError
from ...utils.host import HostPage, get_self_netloc
from ...utils.render import render
from ...utils.request import splice_url
from ...utils.retry import retry
from ...utils.screenshot import screenshot
from .. import Processor as ProcessorMeta
from .cache import Cache
from .constant import BASE_URL, GAME_TYPE, RANK_PERCENTILE
from .model import IORank
from .schemas.base import FailedModel
from .schemas.league_all import LeagueAll
from .schemas.league_all import ValidUser as LeagueAllUser
from .schemas.response import ProcessedData, RawResponse
from .schemas.user import User
from .schemas.user_info import NeverPlayedLeague, NeverRatedLeague, RatedLeague, UserInfo
from .schemas.user_info import SuccessModel as InfoSuccess
from .schemas.user_records import SoloRecord, UserRecords
from .schemas.user_records import SuccessModel as RecordsSuccess
from .typing import Rank

UTC = timezone.utc

driver = get_driver()


def identify_user_info(info: str) -> User | MessageFormatError:
    if match(r'^[a-f0-9]{24}$', info):
        return User(ID=info)
    if match(r'^[a-zA-Z0-9_-]{3,16}$', info):
        return User(name=info.lower())
    return MessageFormatError('用户名/ID不合法')


class Processor(ProcessorMeta):
    user: User
    raw_response: RawResponse
    processed_data: ProcessedData

    @override
    def __init__(self, event_id: int, user: User, command_args: list[str]) -> None:
        super().__init__(event_id, user, command_args)
        self.raw_response = RawResponse()
        self.processed_data = ProcessedData()

    @property
    @override
    def game_platform(self) -> Literal['IO']:
        return GAME_TYPE

    @override
    async def handle_bind(self, platform: str, account: str, bot_info: NBUserInfo) -> UniMessage:
        """处理绑定消息"""
        self.command_type = 'bind'
        await self.get_user()
        if self.user.ID is None:
            raise  # FIXME: 不知道怎么才能把这类型给变过来了
        async with get_session() as session:
            bind_status = await create_or_update_bind(
                session=session,
                chat_platform=platform,
                chat_account=account,
                game_platform=GAME_TYPE,
                game_account=self.user.ID,
            )
        bot_avatar = await get_avatar(bot_info, 'Data URI', '../../static/logo/logo.svg')
        user_info = await self.get_user_info()
        if bind_status in (BindStatus.SUCCESS, BindStatus.UPDATE):
            async with HostPage(
                await render(
                    'bind.j2.html',
                    user_avatar=f'https://tetr.io/user-content/avatars/{user_info.data.user.id}.jpg?rv={user_info.data.user.avatar_revision}'
                    if user_info.data.user.avatar_revision is not None
                    else f'../../identicon?md5={md5(user_info.data.user.id.encode()).hexdigest()}',  # noqa: S324
                    state='unknown',
                    bot_avatar=bot_avatar,
                    game_type=self.game_platform,
                    user_name=user_info.data.user.username.upper(),
                    bot_name=bot_info.user_name,
                    command='io查我',
                )
            ) as page_hash:
                message = UniMessage.image(
                    raw=await screenshot(
                        urlunparse(('http', get_self_netloc(), f'/host/page/{page_hash}.html', '', '', ''))
                    )
                )
        return message

    @override
    async def handle_query(self) -> UniMessage:
        """处理查询消息"""
        self.command_type = 'query'
        await self.get_user()
        user_info, user_records = await gather(self.get_user_info(), self.get_user_records())
        user_name = user_info.data.user.username.upper()
        league = user_info.data.user.league
        sprint = user_records.data.records.sprint
        blitz = user_records.data.records.blitz
        if isinstance(league, RatedLeague) and league.vs is not None:
            if sprint.record is None:
                sprint_value = 'N/A'
            else:
                if not isinstance(sprint.record, SoloRecord):
                    raise WhatTheFuckError('40L记录不是单人记录')
                duration = timedelta(milliseconds=sprint.record.endcontext.final_time).total_seconds()
                sprint_value = f'{duration:.1f}s' if duration < 60 else f'{duration // 60:.0f}m {duration % 60:.1f}s'  # noqa: PLR2004
            if blitz.record is None:
                blitz_value = 'N/A'
            else:
                if not isinstance(blitz.record, SoloRecord):
                    raise WhatTheFuckError('Blitz记录不是单人记录')
                blitz_value = f'{blitz.record.endcontext.score:,}'
            async with HostPage(
                await render(
                    'data.j2.html',
                    user_avatar=f'https://tetr.io/user-content/avatars/{user_info.data.user.id}.jpg?rv={user_info.data.user.avatar_revision}'
                    if user_info.data.user.avatar_revision is not None
                    else f'../../identicon?md5={md5(user_info.data.user.id.encode()).hexdigest()}',  # noqa: S324
                    user_name=user_name,
                    user_sign=user_info.data.user.bio,
                    game_type='TETR.IO',
                    ranking=round(league.glicko, 2),
                    rd=round(league.rd, 2),
                    rank=league.rank,
                    TR=round(league.rating, 2),
                    global_rank=league.standing,
                    lpm=round(lpm := (league.pps * 24), 2),
                    pps=league.pps,
                    apm=league.apm,
                    apl=round(league.apm / lpm, 2),
                    adpm=round(adpm := (league.vs * 0.6), 2),
                    adpl=round(adpm / lpm, 2),
                    vs=league.vs,
                    sprint=sprint_value,
                    blitz=blitz_value,
                    data=[[0, 0]],
                    split_value=0,
                    value_max=0,
                    value_min=0,
                    offset=0,
                    app=(app := (league.apm / (60 * league.pps))),
                    dsps=(dsps := ((league.vs / 100) - (league.apm / 60))),
                    dspp=(dspp := (dsps / league.pps)),
                    ci=150 * dspp - 125 * app + 50 * (league.vs / league.apm) - 25,
                    ge=2 * ((app * dsps) / league.pps),
                )
            ) as page_hash:
                return UniMessage.image(
                    raw=await screenshot(
                        urlunparse(('http', get_self_netloc(), f'/host/page/{page_hash}.html', '', '', ''))
                    )
                )
        # call back
        ret_message = ''
        if isinstance(league, NeverPlayedLeague):
            ret_message += f'用户 {user_name} 没有排位统计数据'
        else:
            if isinstance(league, NeverRatedLeague):
                ret_message += f'用户 {user_name} 暂未完成定级赛, 最近十场的数据:'
            else:
                if league.rank == 'z':
                    ret_message += f'用户 {user_name} 暂无段位, {round(league.rating,2)} TR'
                else:
                    ret_message += (
                        f'{league.rank.upper()} 段用户 {user_name} {round(league.rating,2)} TR (#{league.standing})'
                    )
                ret_message += f', 段位分 {round(league.glicko,2)}±{round(league.rd,2)}, 最近十场的数据:'
            lpm = league.pps * 24
            ret_message += f"\nL'PM: {round(lpm, 2)} ( {league.pps} pps )"
            ret_message += f'\nAPM: {league.apm} ( x{round(league.apm/lpm,2)} )'
            if league.vs is not None:
                adpm = league.vs * 0.6
                ret_message += f'\nADPM: {round(adpm,2)} ( x{round(adpm/lpm,2)} ) ( {league.vs}vs )'
        user_records = await self.get_user_records()
        sprint = user_records.data.records.sprint
        if sprint.record is not None:
            if not isinstance(sprint.record, SoloRecord):
                raise WhatTheFuckError('40L记录不是单人记录')
            ret_message += f'\n40L: {round(sprint.record.endcontext.final_time/1000,2)}s'
            ret_message += f' ( #{sprint.rank} )' if sprint.rank is not None else ''
        blitz = user_records.data.records.blitz
        if blitz.record is not None:
            if not isinstance(blitz.record, SoloRecord):
                raise WhatTheFuckError('Blitz记录不是单人记录')
            ret_message += f'\nBlitz: {blitz.record.endcontext.score}'
            ret_message += f' ( #{blitz.rank} )' if blitz.rank is not None else ''
        return UniMessage(ret_message)

    async def get_user(self) -> None:
        """
        用于获取 UserName 和 UserID 的函数
        """
        if self.user.name is None:
            self.user.name = (await self.get_user_info()).data.user.username
        if self.user.ID is None:
            self.user.ID = (await self.get_user_info()).data.user.id

    async def get_user_info(self) -> InfoSuccess:
        """获取用户数据"""
        if self.processed_data.user_info is None:
            self.raw_response.user_info = await Cache.get(
                splice_url([BASE_URL, 'users/', f'{self.user.ID or self.user.name}'])
            )
            user_info: UserInfo = type_validate_json(UserInfo, self.raw_response.user_info)  # type: ignore[arg-type]
            if isinstance(user_info, FailedModel):
                raise RequestError(f'用户信息请求错误:\n{user_info.error}')
            self.processed_data.user_info = user_info
        return self.processed_data.user_info

    async def get_user_records(self) -> RecordsSuccess:
        """获取Solo数据"""
        if self.processed_data.user_records is None:
            self.raw_response.user_records = await Cache.get(
                splice_url([BASE_URL, 'users/', f'{self.user.ID or self.user.name}/', 'records'])
            )
            user_records: UserRecords = type_validate_json(UserRecords, self.raw_response.user_records)  # type: ignore[arg-type]
            if isinstance(user_records, FailedModel):
                raise RequestError(f'用户Solo数据请求错误:\n{user_records.error}')
            self.processed_data.user_records = user_records
        return self.processed_data.user_records


@scheduler.scheduled_job('cron', hour='0,6,12,18', minute=0)
@retry(exception_type=RequestError, delay=timedelta(minutes=15))
async def get_io_rank_data() -> None:
    league_all: LeagueAll = type_validate_json(
        LeagueAll,  # type: ignore[arg-type]
        (data := await Cache.get(splice_url([BASE_URL, 'users/lists/league/all']))),
    )
    if isinstance(league_all, FailedModel):
        raise RequestError(f'排行榜数据请求错误:\n{league_all.error}')

    def pps(user: LeagueAllUser) -> float:
        return user.league.pps

    def apm(user: LeagueAllUser) -> float:
        return user.league.apm

    def vs(user: LeagueAllUser) -> float:
        return user.league.vs

    def _min(users: list[LeagueAllUser], field: Callable[[LeagueAllUser], float]) -> LeagueAllUser:
        return min(users, key=field)

    def _max(users: list[LeagueAllUser], field: Callable[[LeagueAllUser], float]) -> LeagueAllUser:
        return max(users, key=field)

    def build_extremes_data(
        users: list[LeagueAllUser],
        field: Callable[[LeagueAllUser], float],
        sort: Callable[[list[LeagueAllUser], Callable[[LeagueAllUser], float]], LeagueAllUser],
    ) -> tuple[dict[str, str], float]:
        user = sort(users, field)
        return User(ID=user.id, name=user.username).dict(), field(user)

    data_hash: str | None = await run_sync((await run_sync(sha512)(data)).hexdigest)()
    async with open(get_data_file('nonebot_plugin_tetris_stats', f'{data_hash}.json.zst'), mode='wb') as file:
        await file.write(await run_sync(ZstdCompressor(level=12, threads=-1).compress)(data))

    users = [i for i in league_all.data.users if isinstance(i, LeagueAllUser)]
    rank_to_users: defaultdict[Rank, list[LeagueAllUser]] = defaultdict(list)
    for i in users:
        rank_to_users[i.league.rank].append(i)
    rank_info: list[IORank] = []
    for rank, percentile in RANK_PERCENTILE.items():
        offset = floor((percentile / 100) * len(users)) - 1
        tr_line = users[offset].league.rating
        rank_users = rank_to_users[rank]
        rank_info.append(
            IORank(
                rank=rank,
                tr_line=tr_line,
                player_count=len(rank_users),
                low_pps=(build_extremes_data(rank_users, pps, _min)),
                low_apm=(build_extremes_data(rank_users, apm, _min)),
                low_vs=(build_extremes_data(rank_users, vs, _min)),
                avg_pps=mean({i.league.pps for i in rank_users}),
                avg_apm=mean({i.league.apm for i in rank_users}),
                avg_vs=mean({i.league.vs for i in rank_users}),
                high_pps=(build_extremes_data(rank_users, pps, _max)),
                high_apm=(build_extremes_data(rank_users, apm, _max)),
                high_vs=(build_extremes_data(rank_users, vs, _max)),
                update_time=league_all.cache.cached_at,
                file_hash=data_hash,
            )
        )
    async with get_session() as session:
        session.add_all(rank_info)
        await session.commit()


@driver.on_startup
async def _() -> None:
    async with get_session() as session:
        latest_time = await session.scalar(select(IORank.update_time).order_by(IORank.id.desc()).limit(1))
    if latest_time is None or datetime.now(tz=UTC) - latest_time.replace(tzinfo=UTC) > timedelta(hours=6):
        await get_io_rank_data()
