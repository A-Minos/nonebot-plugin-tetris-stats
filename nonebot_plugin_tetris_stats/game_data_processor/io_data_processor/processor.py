from dataclasses import dataclass
from re import match

from nonebot_plugin_orm import get_session
from pydantic import parse_raw_as

from ...db import create_or_update_bind
from ...utils.exception import MessageFormatError, RequestError, WhatTheFuckError
from ...utils.request import Request, splice_url
from ...utils.typing import GameType
from .. import ProcessedData as ProcessedDataMeta
from .. import Processor as ProcessorMeta
from .. import RawResponse as RawResponseMeta
from .. import User as UserMeta
from .constant import BASE_URL, GAME_TYPE
from .schemas.user_info import FailedModel as InfoFailed
from .schemas.user_info import (
    NeverPlayedLeague,
    NeverRatedLeague,
    UserInfo,
)
from .schemas.user_info import SuccessModel as InfoSuccess
from .schemas.user_records import FailedModel as RecordsFailed
from .schemas.user_records import SoloRecord, UserRecords
from .schemas.user_records import SuccessModel as RecordsSuccess


@dataclass
class User(UserMeta):
    ID: str | None = None
    name: str | None = None


@dataclass
class RawResponse(RawResponseMeta):
    user_info: bytes | None = None
    user_records: bytes | None = None


@dataclass
class ProcessedData(ProcessedDataMeta):
    user_info: InfoSuccess | None = None
    user_records: RecordsSuccess | None = None


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

    def __init__(self, event_id: int, user: User, command_args: list[str]) -> None:
        super().__init__(event_id, user, command_args)
        self.raw_response = RawResponse()
        self.processed_data = ProcessedData()

    @property
    def game_platform(self) -> GameType:
        return GAME_TYPE

    async def handle_bind(self, platform: str, account: str) -> str:
        """处理绑定消息"""
        self.command_type = 'bind'
        await self.get_user()
        if self.user.ID is None:
            raise  # FIXME: 不知道怎么才能把这类型给变过来了
        async with get_session() as session:
            return await create_or_update_bind(
                session=session,
                chat_platform=platform,
                chat_account=account,
                game_platform=GAME_TYPE,
                game_account=self.user.ID,
            )

    async def handle_query(self) -> str:
        """处理查询消息"""
        self.command_type = 'query'
        await self.get_user()
        return await self.generate_message()

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
            self.raw_response.user_info = await Request.request(
                splice_url([BASE_URL, 'users/', f'{self.user.ID or self.user.name}'])
            )
            user_info: UserInfo = parse_raw_as(UserInfo, self.raw_response.user_info)  # type: ignore[arg-type]
            if isinstance(user_info, InfoFailed):
                raise RequestError(f'用户信息请求错误:\n{user_info.error}')
            self.processed_data.user_info = user_info
        return self.processed_data.user_info

    async def get_user_records(self) -> RecordsSuccess:
        """获取Solo数据"""
        if self.processed_data.user_records is None:
            self.raw_response.user_records = await Request.request(
                splice_url(
                    [
                        BASE_URL,
                        'users/',
                        f'{self.user.ID or self.user.name}/',
                        'records',
                    ]
                )
            )
            user_records: UserRecords = parse_raw_as(
                UserRecords,  # type: ignore[arg-type]
                self.raw_response.user_records,
            )
            if isinstance(user_records, RecordsFailed):
                raise RequestError(f'用户Solo数据请求错误:\n{user_records.error}')
            self.processed_data.user_records = user_records
        return self.processed_data.user_records

    async def generate_message(self) -> str:
        """生成消息"""
        user_info = await self.get_user_info()
        user_name = user_info.data.user.username.upper()
        league = user_info.data.user.league
        ret_message = ''
        if isinstance(league, NeverPlayedLeague):
            ret_message += f'用户 {user_name} 没有排位统计数据'
        else:
            if isinstance(league, NeverRatedLeague):
                ret_message += f'用户 {user_name} 暂未完成定级赛, 最近十场的数据:'
            elif league.rank == 'z':
                ret_message += f'用户 {user_name} 暂无段位, {round(league.rating,2)} TR'
            else:
                ret_message += f'{league.rank.upper()} 段用户 {user_name} {round(league.rating,2)} TR (#{league.standing})'
                ret_message += f', 段位分 {round(league.glicko,2)}±{round(league.rd,2)}, 最近十场的数据:'
            lpm = league.pps * 24
            ret_message += f"\nL'PM: {round(lpm, 2)} ( {league.pps} pps )"
            ret_message += (
                f'\nAPM: {league.apm} ( x{round(league.apm/(league.pps*24),2)} )'
            )
            if league.vs is not None:
                adpm = league.vs * 0.6
                ret_message += f'\nADPM: {round(adpm,2)} ( x{round(adpm/lpm,2)} ) ( {league.vs}vs )'
        user_records = await self.get_user_records()
        sprint = user_records.data.records.sprint
        if sprint.record is not None:
            if not isinstance(sprint.record, SoloRecord):
                raise WhatTheFuckError('40L记录不是单人记录')
            ret_message += (
                f'\n40L: {round(sprint.record.endcontext.final_time/1000,2)}s'
            )
            ret_message += f' ( #{sprint.rank} )' if sprint.rank is not None else ''
        blitz = user_records.data.records.blitz
        if blitz.record is not None:
            if not isinstance(blitz.record, SoloRecord):
                raise WhatTheFuckError('Blitz记录不是单人记录')
            ret_message += f'\nBlitz: {blitz.record.endcontext.score}'
            ret_message += f' ( #{blitz.rank} )' if blitz.rank is not None else ''
        return ret_message
