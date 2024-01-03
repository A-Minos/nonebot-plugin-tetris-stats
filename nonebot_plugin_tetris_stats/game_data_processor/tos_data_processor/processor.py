from dataclasses import dataclass
from re import match
from typing import Literal
from urllib.parse import urlencode

from nonebot_plugin_orm import get_session
from pydantic import parse_raw_as

from ...db import create_or_update_bind
from ...utils.exception import MessageFormatError, RequestError
from ...utils.request import Request, splice_url
from .. import Processor as ProcessorMeta
from ..schemas import BaseUser
from .constant import BASE_URL, GAME_TYPE
from .schemas.response import ProcessedData, RawResponse
from .schemas.user_info import SuccessModel as InfoSuccess
from .schemas.user_info import UserInfo
from .schemas.user_profile import UserProfile


class User(BaseUser):
    platform: Literal['TOS'] = GAME_TYPE

    teaid: str | None = None
    name: str | None = None

    @property
    def unique_identifier(self) -> str:
        if self.teaid is None:
            raise ValueError('不完整的User!')
        return self.teaid


@dataclass
class GameData:
    num: int
    pps: float
    lpm: float
    apm: float
    adpm: float
    apl: float
    adpl: float
    vs: float


def identify_user_info(info: str) -> User | MessageFormatError:
    if (
        match(
            r'^(?!\.)(?!com[0-9]$)(?!con$)(?!lpt[0-9]$)(?!nul$)(?!prn$)[^\-][^\+][^\|\*\?\\\s\!:<>/$"]*[^\.\|\*\?\\\s\!:<>/$"]+$',
            info,
        )
        and info.isdigit() is False
        and 2 <= len(info) <= 18  # noqa: PLR2004
    ):
        return User(name=info)
    if info.startswith(('onebot-', 'qqguild-', 'kook-', 'discord-')) and info.split('-', maxsplit=1)[1].isdigit():
        return User(teaid=info)
    return MessageFormatError('用户名/QQ号不合法')


class Processor(ProcessorMeta):
    user: User
    raw_response: RawResponse
    processed_data: ProcessedData

    def __init__(self, event_id: int, user: User, command_args: list[str]) -> None:
        super().__init__(event_id, user, command_args)
        self.raw_response = RawResponse(user_profile={})
        self.processed_data = ProcessedData(user_profile={})

    @property
    def game_platform(self) -> Literal['TOS']:
        return GAME_TYPE

    async def handle_bind(self, platform: str, account: str) -> str:
        """处理绑定消息"""
        self.command_type = 'bind'
        await self.get_user()
        async with get_session() as session:
            return await create_or_update_bind(
                session=session,
                chat_platform=platform,
                chat_account=account,
                game_platform=GAME_TYPE,
                game_account=self.user.unique_identifier,
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
            self.user.name = (await self.get_user_info()).data.name
        if self.user.teaid is None:
            self.user.teaid = (await self.get_user_info()).data.teaid

    async def get_user_info(self) -> InfoSuccess:
        """获取用户信息"""
        if self.processed_data.user_info is None:
            if self.user.teaid is not None:
                url = splice_url(
                    [
                        BASE_URL,
                        'getTeaIdInfo',
                        f'?{urlencode({"teaId":self.user.teaid})}',
                    ]
                )
            else:
                url = splice_url(
                    [
                        BASE_URL,
                        'getUsernameInfo',
                        f'?{urlencode({"username":self.user.name})}',
                    ]
                )
            self.raw_response.user_info = await Request.request(url)
            user_info: UserInfo = parse_raw_as(UserInfo, self.raw_response.user_info)  # type: ignore[arg-type]
            if not isinstance(user_info, InfoSuccess):
                raise RequestError(f'用户信息请求错误:\n{user_info.error}')
            self.processed_data.user_info = user_info
        return self.processed_data.user_info

    async def get_user_profile(self, other_parameter: dict[str, str | bytes] | None = None) -> UserProfile:
        """获取用户数据"""
        if other_parameter is None:
            other_parameter = {}
        params = urlencode(dict(sorted(other_parameter.items())))
        if self.processed_data.user_profile.get(params) is None:
            self.raw_response.user_profile[params] = await Request.request(
                splice_url(
                    [
                        BASE_URL,
                        'getProfile',
                        f'?{urlencode({"id":self.user.teaid or self.user.name,**other_parameter})}',
                    ]
                )
            )
            self.processed_data.user_profile[params] = UserProfile.parse_raw(self.raw_response.user_profile[params])
        return self.processed_data.user_profile[params]

    async def get_game_data(self) -> GameData | None:
        """获取游戏数据"""
        user_profile = await self.get_user_profile()
        if user_profile.data == []:
            return None
        weighted_total_lpm = weighted_total_apm = weighted_total_adpm = 0.0
        total_time = 0.0
        num = 0
        for i in user_profile.data:
            # 排除单人局和时间为0的游戏
            # 茶: 不计算没挖掘的局, 即使apm和lpm也如此
            if i.num_players == 1 or i.time == 0 or i.dig is None:
                continue
            # 加权计算
            time = i.time / 1000
            lpm = 24 * (i.pieces / time)
            apm = (i.attack / time) * 60
            adpm = ((i.attack + i.dig) / time) * 60
            weighted_total_lpm += lpm * time
            weighted_total_apm += apm * time
            weighted_total_adpm += adpm * time
            total_time += time
            num += 1
            if num == 50:  # noqa: PLR2004  # TODO: 将查询局数作为可选命令参数
                break
        if num == 0:
            return None
        # TODO: 如果有效局数不满50, 没有无dig信息的局, 且userData['data']内有50个局, 则继续往前获取信息
        lpm = weighted_total_lpm / total_time
        apm = weighted_total_apm / total_time
        adpm = weighted_total_adpm / total_time
        return GameData(
            num=num,
            pps=round(lpm / 24, 2),
            lpm=round(lpm, 2),
            apm=round(apm, 2),
            adpm=round(adpm, 2),
            apl=round((apm / lpm), 2),
            adpl=round((adpm / lpm), 2),
            vs=round((adpm / 60 * 100), 2),
        )

    async def generate_message(self) -> str:
        """生成消息"""
        user_info = (await self.get_user_info()).data
        message = f'用户 {user_info.name} ({user_info.teaid}) '
        if user_info.ranked_games == '0':
            message += '暂无段位统计数据'
        else:
            message += f', 段位分 {round(float(user_info.rating_now),2)}±{round(float(user_info.rd_now),2)} ({round(float(user_info.vol_now),2)}) '
        game_data = await self.get_game_data()
        if game_data is None:
            message += ', 暂无游戏数据'
        else:
            message += f', 最近 {game_data.num} 局数据'
            message += f"\nL'PM: {game_data.lpm} ( {game_data.pps} pps )"
            message += f'\nAPM: {game_data.apm} ( x{game_data.apl} )'
            message += f'\nADPM: {game_data.adpm} ( x{game_data.adpl} ) ( {game_data.vs}vs )'
        message += f'\n40L: {float(user_info.pb_sprint)/1000:.2f}s' if user_info.pb_sprint != '2147483647' else ''
        message += f'\nMarathon: {user_info.pb_marathon}' if user_info.pb_marathon != '0' else ''
        message += f'\nChallenge: {user_info.pb_challenge}' if user_info.pb_challenge != '0' else ''
        return message
