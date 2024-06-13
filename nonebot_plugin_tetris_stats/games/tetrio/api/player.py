from typing import overload

from nonebot.compat import type_validate_json

from ....db import anti_duplicate_add
from ....utils.exception import RequestError
from ....utils.request import splice_url
from ..constant import BASE_URL, USER_ID, USER_NAME
from .cache import Cache
from .models import TETRIOHistoricalData
from .schemas.base import FailedModel
from .schemas.user import User
from .schemas.user_info import UserInfo, UserInfoSuccess
from .schemas.user_records import SoloModeRecord, UserRecords, UserRecordsSuccess, Zen


class Player:
    @overload
    def __init__(self, *, user_id: str, trust: bool = False): ...
    @overload
    def __init__(self, *, user_name: str, trust: bool = False): ...
    def __init__(self, *, user_id: str | None = None, user_name: str | None = None, trust: bool = False):
        self.user_id = user_id
        self.user_name = user_name
        if not trust:
            if self.user_id is not None:
                if not USER_ID.match(self.user_id):
                    msg = 'Invalid user id'
                    raise ValueError(msg)
            elif self.user_name is not None:
                if not USER_NAME.match(self.user_name):
                    msg = 'Invalid user name'
                    raise ValueError(msg)
            else:
                msg = 'Invalid user'
                raise ValueError(msg)
        self.__user: User | None = None
        self._user_info: UserInfoSuccess | None = None
        self._user_records: UserRecordsSuccess | None = None

    @property
    def _request_user_parameter(self) -> str:
        if self.user_id is not None:
            return self.user_id
        if self.user_name is not None:
            return self.user_name.lower()
        msg = 'Invalid user'
        raise ValueError(msg)

    @property
    async def user(self) -> User:
        if self.__user is None:
            user_info = await self.get_info()
            self.__user = User(
                ID=user_info.data.user.id,
                name=user_info.data.user.username,
            )
            self.user_id = user_info.data.user.id
            self.user_name = user_info.data.user.username
        return self.__user

    async def get_info(self) -> UserInfoSuccess:
        """Get User Info"""
        if self._user_info is None:
            raw_user_info = await Cache.get(splice_url([BASE_URL, 'users/', f'{self._request_user_parameter}']))
            user_info: UserInfo = type_validate_json(UserInfo, raw_user_info)  # type: ignore[arg-type]
            if isinstance(user_info, FailedModel):
                msg = f'用户信息请求错误:\n{user_info.error}'
                raise RequestError(msg)
            self._user_info = user_info
            await anti_duplicate_add(
                TETRIOHistoricalData,
                TETRIOHistoricalData(
                    user_unique_identifier=(await self.user).unique_identifier,
                    api_type='User Info',
                    data=user_info,
                    update_time=user_info.cache.cached_at,
                ),
            )
        return self._user_info

    async def get_records(self) -> UserRecordsSuccess:
        """Get User Records"""
        if self._user_records is None:
            raw_user_records = await Cache.get(
                splice_url([BASE_URL, 'users/', f'{self._request_user_parameter}/', 'records'])
            )
            user_records: UserRecords = type_validate_json(UserRecords, raw_user_records)  # type: ignore[arg-type]
            if isinstance(user_records, FailedModel):
                msg = f'用户Solo数据请求错误:\n{user_records.error}'
                raise RequestError(msg)
            self._user_records = user_records
            await anti_duplicate_add(
                TETRIOHistoricalData,
                TETRIOHistoricalData(
                    user_unique_identifier=(await self.user).unique_identifier,
                    api_type='User Records',
                    data=user_records,
                    update_time=user_records.cache.cached_at,
                ),
            )
        return self._user_records

    @property
    async def sprint(self) -> SoloModeRecord:
        return (await self.get_records()).data.records.sprint

    @property
    async def blitz(self) -> SoloModeRecord:
        return (await self.get_records()).data.records.blitz

    @property
    async def zen(self) -> Zen:
        return (await self.get_records()).data.zen
