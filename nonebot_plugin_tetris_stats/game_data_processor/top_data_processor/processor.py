from contextlib import suppress
from dataclasses import dataclass
from io import StringIO
from re import match
from typing import Literal, NoReturn
from urllib.parse import urlencode

from lxml import etree
from nonebot_plugin_orm import get_session
from pandas import read_html

from ...db import create_or_update_bind
from ...utils.exception import MessageFormatError, RequestError
from ...utils.request import Request, splice_url
from .. import Processor as ProcessorMeta
from ..schemas import BaseUser
from .constant import BASE_URL, GAME_TYPE
from .schemas.response import ProcessedData, RawResponse


class User(BaseUser):
    platform: Literal['TOP'] = GAME_TYPE

    name: str

    @property
    def unique_identifier(self) -> str:
        return self.name


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


class Processor(ProcessorMeta):
    user: User
    raw_response: RawResponse
    processed_data: ProcessedData

    def __init__(self, event_id: int, user: User, command_args: list[str]) -> None:
        super().__init__(event_id, user, command_args)
        self.raw_response = RawResponse()
        self.processed_data = ProcessedData()

    @property
    def game_platform(self) -> Literal['TOP']:
        return GAME_TYPE

    async def handle_bind(self, platform: str, account: str) -> str:
        """处理绑定消息"""
        self.command_type = 'bind'
        await self.check_user()
        async with get_session() as session:
            return await create_or_update_bind(
                session=session,
                chat_platform=platform,
                chat_account=account,
                game_platform=GAME_TYPE,
                game_account=self.user.name,
            )

    async def handle_query(self) -> str:
        """处理查询消息"""
        self.command_type = 'query'
        await self.check_user()
        return await self.generate_message()

    async def get_user_profile(self) -> str:
        """获取用户信息"""
        if self.processed_data.user_profile is None:
            url = splice_url([BASE_URL, 'profile.php', f'?{urlencode({"user":self.user.name})}'])
            self.raw_response.user_profile = await Request.request(url, is_json=False)
            self.processed_data.user_profile = self.raw_response.user_profile.decode()
        return self.processed_data.user_profile

    async def check_user(self) -> None | NoReturn:
        if 'user not found!' in await self.get_user_profile():
            raise RequestError('用户不存在!')
        return None

    async def get_user_name(self) -> str:
        """获取用户名"""
        data = etree.HTML(await self.get_user_profile()).xpath('//div[@class="mycontent"]/h1/text()')
        return data[0].replace("'s profile", '')

    async def get_game_data(self) -> GameData:
        """获取游戏统计数据"""
        html = etree.HTML(await self.get_user_profile())
        day = None
        with suppress(ValueError):
            day = Data(
                lpm=float(str(html.xpath('//div[@class="mycontent"]/text()[3]')[0]).replace('lpm:', '').strip()),
                apm=float(str(html.xpath('//div[@class="mycontent"]/text()[4]')[0]).replace('apm:', '').strip()),
            )
        table = StringIO(
            etree.tostring(
                html.xpath('//div[@class="mycontent"]/table[@class="mytable"]')[0],
                encoding='utf-8',
            ).decode()
        )
        dataframe = read_html(table, encoding='utf-8', header=0)[0]
        total = Data(lpm=dataframe['lpm'].mean(), apm=dataframe['apm'].mean()) if len(dataframe) != 0 else None
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
