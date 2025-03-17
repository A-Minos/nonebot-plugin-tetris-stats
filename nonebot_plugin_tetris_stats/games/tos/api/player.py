from datetime import datetime, timezone
from typing import cast, overload

from httpx import TimeoutException
from nonebot.compat import type_validate_json
from yarl import URL

from ....config.config import config
from ....db import anti_duplicate_add
from ....utils.exception import RequestError
from ....utils.request import Request
from ..constant import BASE_URL, USER_NAME
from .models import TOSHistoricalData
from .schemas.user import User
from .schemas.user_info import UserInfo, UserInfoSuccess
from .schemas.user_profile import UserProfile

UTC = timezone.utc

request = Request(config.tetris.proxy.tos or config.tetris.proxy.main)


class Player:
    @overload
    def __init__(self, *, teaid: str, trust: bool = False): ...
    @overload
    def __init__(self, *, user_name: str, trust: bool = False): ...
    def __init__(self, *, teaid: str | None = None, user_name: str | None = None, trust: bool = False):
        self.teaid = teaid
        self.user_name = user_name
        if not trust:
            if self.teaid is not None:
                if (
                    not self.teaid.startswith(('onebot-', 'qqguild-', 'kook-', 'discord-'))
                    or not self.teaid.split('-', maxsplit=1)[1].isdigit()
                ):
                    msg = 'Invalid teaid'
                    raise ValueError(msg)
            elif self.user_name is not None:
                if not USER_NAME.match(self.user_name) or self.user_name.isdigit() or 2 > len(self.user_name) > 18:  # noqa: PLR2004
                    msg = 'Invalid user name'
                    raise ValueError(msg)
            else:
                msg = 'Invalid user'
                raise ValueError(msg)
        self.__user: User | None = None
        self._user_info: UserInfoSuccess | None = None
        self._user_profile: dict[str, UserProfile] = {}

    @property
    async def user(self) -> User:
        if self.__user is None:
            user_info = await self.get_info()
            self.__user = User(teaid=user_info.data.teaid, name=user_info.data.name)
            self.teaid = user_info.data.teaid
            self.user_name = user_info.data.name
        return self.__user

    async def get_info(self) -> UserInfoSuccess:
        """获取用户信息"""
        if self._user_info is None:
            if self.teaid is not None:
                path = 'getTeaIdInfo'
                query = {'teaId': self.teaid}
            else:
                path = 'getUsernameInfo'
                query = {'username': cast('str', self.user_name)}
            raw_user_info = await request.failover_request(
                [i / path % query for i in BASE_URL], failover_code=[502], failover_exc=(TimeoutException,)
            )
            user_info: UserInfo = type_validate_json(UserInfo, raw_user_info)  # type: ignore[arg-type]
            if not isinstance(user_info, UserInfoSuccess):
                msg = f'用户信息请求错误:\n{user_info.error}'
                raise RequestError(msg)
            self._user_info = user_info
            await anti_duplicate_add(
                TOSHistoricalData(
                    user_unique_identifier=(await self.user).unique_identifier,
                    api_type='User Info',
                    data=user_info,
                    update_time=datetime.now(UTC),
                ),
            )
        return self._user_info

    async def get_profile(self, other_parameter: dict[str, str | bytes] | None = None) -> UserProfile:
        """获取用户数据"""
        if other_parameter is None:
            other_parameter = {}
        params = (URL('') % dict(sorted(other_parameter.items()))).human_repr()
        if self._user_profile.get(params) is None:
            raw_user_profile = await request.failover_request(
                [
                    i / 'getProfile' % {'id': self.teaid or cast('str', self.user_name), **other_parameter}
                    for i in BASE_URL
                ],
                failover_code=[502],
                failover_exc=(TimeoutException,),
            )
            self._user_profile[params] = type_validate_json(UserProfile, raw_user_profile)
            await anti_duplicate_add(
                TOSHistoricalData(
                    user_unique_identifier=(await self.user).unique_identifier,
                    api_type='User Profile',
                    data=self._user_profile[params],
                    update_time=datetime.now(UTC),
                ),
            )
        return self._user_profile[params]
