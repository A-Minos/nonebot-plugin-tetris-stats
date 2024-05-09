from contextlib import suppress
from dataclasses import dataclass
from io import StringIO
from re import match
from typing import Literal
from urllib.parse import urlencode, urlunparse

from lxml import etree
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_userinfo import UserInfo  # type: ignore[import-untyped]
from pandas import read_html
from typing_extensions import override

from ...db import BindStatus, create_or_update_bind
from ...utils.avatar import get_avatar
from ...utils.exception import MessageFormatError, RequestError
from ...utils.host import HostPage, get_self_netloc
from ...utils.render import Bind, render
from ...utils.request import Request, splice_url
from ...utils.screenshot import screenshot
from .. import Processor as ProcessorMeta
from ..schemas import BaseUser
from .constant import BASE_URL, GAME_TYPE
from .schemas.response import ProcessedData, RawResponse


class User(BaseUser):
    platform: Literal['TOP'] = GAME_TYPE

    name: str

    @property
    @override
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

    @override
    def __init__(self, event_id: int, user: User, command_args: list[str]) -> None:
        super().__init__(event_id, user, command_args)
        self.raw_response = RawResponse()
        self.processed_data = ProcessedData()

    @property
    @override
    def game_platform(self) -> Literal['TOP']:
        return GAME_TYPE

    @override
    async def handle_bind(self, platform: str, account: str, bot_info: UserInfo, user_info: UserInfo) -> UniMessage:
        """处理绑定消息"""
        self.command_type = 'bind'
        await self.check_user()
        async with get_session() as session:
            bind_status = await create_or_update_bind(
                session=session,
                chat_platform=platform,
                chat_account=account,
                game_platform=GAME_TYPE,
                game_account=self.user.name,
            )
        if bind_status in (BindStatus.SUCCESS, BindStatus.UPDATE):
            async with HostPage(
                await render(
                    'binding',
                    Bind(
                        platform=self.game_platform,
                        status='unknown',
                        user=Bind.People(
                            avatar=await get_avatar(user_info, 'Data URI', None),
                            name=(await self.get_user_name()).upper(),
                        ),
                        bot=Bind.People(
                            avatar=await get_avatar(bot_info, 'Data URI', '../../static/logo/logo.svg'),
                            name=bot_info.user_name,
                        ),
                        command='top查我',
                    ),
                )
            ) as page_hash:
                message = UniMessage.image(
                    raw=await screenshot(urlunparse(('http', get_self_netloc(), f'/host/{page_hash}.html', '', '', '')))
                )
        return message

    @override
    async def handle_query(self) -> UniMessage:
        """处理查询消息"""
        self.command_type = 'query'
        await self.check_user()
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
        return UniMessage(message)

    async def get_user_profile(self) -> str:
        """获取用户信息"""
        if self.processed_data.user_profile is None:
            url = splice_url([BASE_URL, 'profile.php', f'?{urlencode({"user":self.user.name})}'])
            self.raw_response.user_profile = await Request.request(url, is_json=False)
            self.processed_data.user_profile = self.raw_response.user_profile.decode()
        return self.processed_data.user_profile

    async def check_user(self) -> None:
        if 'user not found!' in await self.get_user_profile():
            raise RequestError('用户不存在!')

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
