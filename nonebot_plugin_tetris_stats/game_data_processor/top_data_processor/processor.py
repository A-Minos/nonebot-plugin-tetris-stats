from dataclasses import dataclass
from io import StringIO
from re import match
from urllib.parse import urlencode

from lxml import etree
from nonebot_plugin_orm import AsyncSession, get_session
from pandas import read_html
from sqlalchemy import select

from ...db.models import Bind
from ...utils.exception import MessageFormatError, RequestError
from ...utils.request import Request, splice_url
from ...utils.typing import CommandType
from .constant import BASE_URL


@dataclass
class User:
    name: str


@dataclass
class RawResponse:
    user_profile: bytes | None = None


@dataclass
class ProcessedData:
    user_profile: str | None = None


@dataclass
class Data:
    lpm: float
    apm: float


@dataclass
class GameData:
    day: Data | None
    total: Data | None


def identify_user_info(info: str) -> User | MessageFormatError:
    if match(r'^[a-zA-Z0-9_]{1,16}$', info):
        return User(name=info)
    return MessageFormatError('用户名不合法')


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

    async def handle_bind(self, source_id: str) -> str:
        """处理绑定消息"""
        self.command_type = 'bind'
        await self.check_user()
        async with get_session() as session:
            bind = (
                await session.scalars(select(Bind).where(Bind.qq_number == source_id))
            ).one_or_none()
            if bind is None:
                bind = Bind(qq_number=source_id, TOP_id=self.user.name)
                session.add(bind)
                message = '绑定成功'
            elif bind.TOP_id is None:
                message = '绑定成功'
            else:
                message = '更新成功'
            bind.TOP_id = self.user.name
            await session.commit()
        return message

    async def handle_query(self) -> str:
        """处理查询消息"""
        self.command_type = 'query'
        await self.check_user()
        return await self.generate_message()

    async def get_user_profile(self) -> str:
        """获取用户信息"""
        if self.processed_data.user_profile is None:
            url = splice_url(
                [BASE_URL, 'profile.php', f'?{urlencode({"user":self.user.name})}']
            )
            self.raw_response.user_profile = await Request.request(url, json=False)
            self.processed_data.user_profile = self.raw_response.user_profile.decode()
        return self.processed_data.user_profile

    async def check_user(self):
        if 'user not found!' in await self.get_user_profile():
            raise RequestError('用户不存在!')

    async def get_user_name(self) -> str:
        """获取用户名"""
        data = etree.HTML(await self.get_user_profile()).xpath(
            '//div[@class="mycontent"]/h1/text()'
        )
        return data[0].replace("'s profile", '')

    async def get_game_data(self) -> GameData:
        """获取游戏统计数据"""
        html = etree.HTML(await self.get_user_profile())
        day = None
        try:
            day = Data(
                lpm=float(
                    str(html.xpath('//div[@class="mycontent"]/text()[3]')[0])
                    .replace('lpm:', '')
                    .strip()
                ),
                apm=float(
                    str(html.xpath('//div[@class="mycontent"]/text()[4]')[0])
                    .replace('apm:', '')
                    .strip()
                ),
            )
        except ValueError:
            pass
        table = StringIO(
            etree.tostring(
                html.xpath('//div[@class="mycontent"]/table[@class="mytable"]')[0],
                encoding='utf-8',
            ).decode()
        )
        dataframe = read_html(table, encoding='utf-8', header=0)[0]
        if len(dataframe) == 0:
            total = Data(
                lpm=dataframe['lpm'].mean(),
                apm=dataframe['apm'].mean(),
            )
        else:
            total = None
        return GameData(day=day, total=total)

    async def generate_message(self) -> str:
        """生成消息"""
        game_data = await self.get_game_data()
        message = ''
        if game_data.day is not None:
            message += f'用户 {self.user.name} 24小时内统计数据为: '
            message += f"\nL'PM: {round(game_data.day.lpm,2)} ( {round(game_data.day.lpm/24,2)} pps )"
            message += f'\nAPM: {round(game_data.day.apm,2)} ( x{round(game_data.day.apm/game_data.day.lpm,2)} )'
        else:
            message += f'用户 {self.user.name} 暂无24小时内统计数据'
        if game_data.total is not None:
            message += '\n历史统计数据为: '
            message += f"\nL'PM: {round(game_data.total.lpm,2)} ( {round(game_data.total.lpm/24,2)} pps )"
            message += f'\nAPM: {round(game_data.total.apm,2)} ( x{round(game_data.total.apm/game_data.total.lpm,2)} )'
        else:
            message += '\n暂无历史统计数据'
        return message
