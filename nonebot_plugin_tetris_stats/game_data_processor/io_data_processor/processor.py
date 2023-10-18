from dataclasses import dataclass
from re import match

from nonebot_plugin_orm import AsyncSession, get_session
from pydantic import parse_raw_as
from sqlalchemy import select

from ...db.models import Bind
from ...utils.exception import MessageFormatError, RequestError, WhatTheFuckError
from ...utils.recorder import Recorder
from ...utils.request import Request
from ...utils.typing import CommandType
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
class User:
    ID: str | None = None
    name: str | None = None


@dataclass
class RawResponse:
    user_info: bytes | None = None
    user_records: bytes | None = None


@dataclass
class ProcessedData:
    user_info: InfoSuccess | None = None
    user_records: RecordsSuccess | None = None


def identify_user_info(info: str) -> User:
    if match(r'^[a-f0-9]{24}$', info):
        return User(ID=info)
    if match(r'^[a-zA-Z0-9_-]{3,16}$', info):
        return User(name=info.lower())
    else:
        raise MessageFormatError('用户名/ID不合法')


async def query_bind_info(session: AsyncSession, qq_number: str) -> Bind | None:
    return (
        await session.scalars(select(Bind).where(Bind.qq_number == qq_number))
    ).one_or_none()


class Processor:
    event_id: int
    command_type: CommandType
    command_args: list[str]
    user: User
    raw_response: RawResponse
    processed_data: ProcessedData

    def __init__(
        self,
        event_id: int,
        user: User,
        command_args: list[str],
    ) -> None:
        self.event_id = event_id
        self.command_args = command_args
        self.user = user
        self.raw_response = RawResponse()
        self.processed_data = ProcessedData()

    @Recorder.recorder(Recorder.send)
    async def handle_bind(self, source_id: str) -> str:
        """处理绑定消息"""
        self.command_type = 'bind'
        await self.get_user()
        async with get_session() as session:
            bind = (
                await session.scalars(select(Bind).where(Bind.qq_number == source_id))
            ).one_or_none()
            if bind is None:
                bind = Bind(qq_number=source_id, IO_id=self.user.ID)
                session.add(bind)
                message = '绑定成功'
            elif bind.IO_id is None:
                message = '绑定成功'
            else:
                message = '更新成功'
            bind.IO_id = self.user.ID
            await session.commit()
        return message

    @Recorder.recorder(Recorder.send)
    async def handle_query(self):
        """处理查询消息"""
        self.command_type = 'query'
        await self.get_user()
        return await self.generate_message()

    async def get_user(self) -> None:
        """
        用于获取 UserName 和 UserID 的函数

        如果 UserName 和 UserID 都是 None 会 raise 一个 WhatTheFuckException (
        """
        if self.user.ID is None and self.user.name is None:
            raise WhatTheFuckError('为什么 UserName 和 UserID 都没有')
        if self.user.name is None:
            self.user.name = (await self.get_user_info()).data.user.username
        if self.user.ID is None:
            self.user.ID = (await self.get_user_info()).data.user.id

    async def get_user_info(self) -> InfoSuccess:
        """获取用户数据"""
        if self.processed_data.user_info is None:
            self.raw_response.user_info = await Request.request(
                f'https://ch.tetr.io/api/users/{self.user.ID or self.user.name}'
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
                f'https://ch.tetr.io/api/users/{self.user.ID or self.user.name}/records'
            )
            user_records: UserRecords = parse_raw_as(
                UserRecords, self.raw_response.user_records  # type: ignore[arg-type]
            )
            if isinstance(user_records, RecordsFailed):
                raise RequestError(f'用户Solo数据请求错误:\n{user_records.error}')
            self.processed_data.user_records = user_records
        return self.processed_data.user_records

    async def generate_message(self) -> str:
        """生成消息"""
        user_name = (await self.get_user_info()).data.user.username
        user_info = await self.get_user_info()
        league = user_info.data.user.league
        ret_message = ''
        if isinstance(league, NeverPlayedLeague):
            ret_message += f'用户 {user_name} 没有排位统计数据'
        else:
            if isinstance(league, NeverRatedLeague):
                ret_message += f'用户 {user_name} 暂未完成定级赛, 最近十场的数据:'
            elif league.rank == 'z':
                ret_message += f'用户 {user_name} 暂无段位, {league.rating} TR'
            else:
                ret_message += f'{league.rank.upper()} 段用户 {user_name} {league.rating} TR (#{league.standing})'
                ret_message += f', 段位分 {league.glicko}±{league.rd}, 最近十场的数据:'
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
