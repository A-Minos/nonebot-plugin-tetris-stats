from enum import Enum
from types import MappingProxyType
from typing import Literal, NamedTuple, cast, overload

from async_lru import alru_cache
from nonebot.compat import type_validate_json

from ....db import anti_duplicate_add
from ....utils.exception import RequestError
from ..constant import BASE_URL, USER_ID, USER_NAME
from .cache import Cache
from .models import TETRIOHistoricalData
from .schemas.base import FailedModel
from .schemas.labs.leagueflow import LeagueFlow, LeagueFlowSuccess
from .schemas.records.solo import Solo as SoloRecord
from .schemas.records.solo import SoloSuccessModel as RecordsSoloSuccessModel
from .schemas.summaries import (
    AchievementsSuccessModel,
    SummariesModel,
    ZenithSuccessModel,
    ZenSuccessModel,
)
from .schemas.summaries import (
    SoloSuccessModel as SummariesSoloSuccessModel,
)
from .schemas.summaries.base import User as SummariesUser
from .schemas.summaries.league import LeagueSuccessModel
from .schemas.user import User
from .schemas.user_info import UserInfo, UserInfoSuccess
from .typedefs import Records, Summaries


class RecordModeType(str, Enum):
    Sprint = '40l'
    Blitz = 'blitz'


class RecordType(str, Enum):
    Top = 'top'
    Recent = 'recent'
    Progression = 'progression'


class RecordKey(NamedTuple):
    mode_type: RecordModeType
    record_type: RecordType

    def to_records(self) -> Records:
        return cast('Records', f'{self.mode_type.value}_{self.record_type.value}')


class Player:
    __SUMMARIES_MAPPING: MappingProxyType[Summaries, type[SummariesModel]] = MappingProxyType(
        {
            '40l': SummariesSoloSuccessModel,
            'blitz': SummariesSoloSuccessModel,
            'zenith': ZenithSuccessModel,
            'zenithex': ZenithSuccessModel,
            'league': LeagueSuccessModel,
            'zen': ZenSuccessModel,
            'achievements': AchievementsSuccessModel,
        }
    )

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
        self._summaries: dict[Summaries, SummariesModel] = {}
        self._records: dict[RecordKey, RecordsSoloSuccessModel] = {}
        self._leagueflow: LeagueFlowSuccess | None = None

    @property
    def _request_user_parameter(self) -> str:
        return self.user_id or cast('str', self.user_name).lower()

    @property
    async def user(self) -> User:
        if self.__user is not None:
            return self.__user
        if (user := (await self._get_local_summaries_user())) is not None:
            self.__user = User(
                ID=user.id,
                name=user.username,
            )
        else:
            user_info = await self.get_info()
            self.__user = User(
                ID=user_info.data.id,
                name=user_info.data.username,
            )
        self.user_id = self.__user.ID
        self.user_name = self.__user.name
        return self.__user

    async def get_info(self) -> UserInfoSuccess:
        """Get User Info"""
        if self._user_info is None:
            raw_user_info = await Cache.get(BASE_URL / 'users' / self._request_user_parameter)
            user_info: UserInfo = type_validate_json(UserInfo, raw_user_info)  # type: ignore[arg-type]
            if isinstance(user_info, FailedModel):
                msg = f'用户信息请求错误:\n{user_info.error}'
                raise RequestError(msg)
            self._user_info = user_info
            await anti_duplicate_add(
                TETRIOHistoricalData(
                    user_unique_identifier=(await self.user).unique_identifier,
                    api_type='User Info',
                    data=user_info,
                    update_time=user_info.cache.cached_at,
                ),
            )
        return self._user_info

    @overload
    async def get_summaries(self, summaries_type: Literal['40l', 'blitz']) -> SummariesSoloSuccessModel: ...
    @overload
    async def get_summaries(self, summaries_type: Literal['zenith', 'zenithex']) -> ZenithSuccessModel: ...
    @overload
    async def get_summaries(self, summaries_type: Literal['zen']) -> ZenSuccessModel: ...
    @overload
    async def get_summaries(self, summaries_type: Literal['league']) -> LeagueSuccessModel: ...
    @overload
    async def get_summaries(self, summaries_type: Literal['achievements']) -> AchievementsSuccessModel: ...

    async def get_summaries(self, summaries_type: Summaries) -> SummariesModel:
        if summaries_type not in self._summaries:
            raw_summaries = await Cache.get(
                BASE_URL / 'users' / self._request_user_parameter / 'summaries' / summaries_type
            )
            summaries: SummariesModel | FailedModel = type_validate_json(
                self.__SUMMARIES_MAPPING[summaries_type] | FailedModel,  # type: ignore[arg-type]
                raw_summaries,
            )
            if isinstance(summaries, FailedModel):
                msg = f'用户Summaries数据请求错误:\n{summaries.error}'
                raise RequestError(msg)
            self._summaries[summaries_type] = summaries
            await anti_duplicate_add(
                TETRIOHistoricalData(
                    user_unique_identifier=(await self.user).unique_identifier,
                    api_type=summaries_type,
                    data=summaries,
                    update_time=summaries.cache.cached_at,
                ),
            )
        return self._summaries[summaries_type]

    async def get_leagueflow(self) -> LeagueFlowSuccess:
        if self._leagueflow is None:
            leagueflow: LeagueFlow = type_validate_json(
                LeagueFlow,  # type: ignore[arg-type]
                await Cache.get(BASE_URL / 'labs/leagueflow' / self._request_user_parameter),
            )
            if isinstance(leagueflow, FailedModel):
                msg = f'League 历史记录请求错误:\n{leagueflow.error}'
                raise RequestError(msg)
            self._leagueflow = leagueflow
        return self._leagueflow

    @property
    async def sprint(self) -> SummariesSoloSuccessModel:
        return await self.get_summaries('40l')

    @property
    async def blitz(self) -> SummariesSoloSuccessModel:
        return await self.get_summaries('blitz')

    @property
    async def zen(self) -> ZenSuccessModel:
        return await self.get_summaries('zen')

    @property
    async def league(self) -> LeagueSuccessModel:
        return await self.get_summaries('league')

    async def _get_local_summaries_user(self) -> SummariesUser | None:
        allow_summaries: set[Literal['40l', 'blitz', 'zenith', 'zenithex']] = {
            '40l',
            'blitz',
            'zenith',
            'zenithex',
        }
        if has_summaries := (allow_summaries & self._summaries.keys()):
            for i in has_summaries:
                if (record := (await self.get_summaries(i)).data.record) is not None:
                    return record.user
        return None

    @property
    @alru_cache
    async def avatar_revision(self) -> int | None:
        if self._user_info is not None:
            return self._user_info.data.avatar_revision
        if (user := (await self._get_local_summaries_user())) is not None:
            return user.avatar_revision
        return (await self.get_info()).data.avatar_revision

    @property
    @alru_cache
    async def banner_revision(self) -> int | None:
        if self._user_info is not None:
            return self._user_info.data.banner_revision
        if (user := (await self._get_local_summaries_user())) is not None:
            return user.banner_revision
        return (await self.get_info()).data.banner_revision

    async def get_records(self, mode_type: RecordModeType, records_type: RecordType) -> RecordsSoloSuccessModel:
        if (record_key := RecordKey(mode_type, records_type)) not in self._records:
            raw_records = await Cache.get(
                BASE_URL / 'users' / self._request_user_parameter / 'records' / mode_type / records_type,
            )
            records: RecordsSoloSuccessModel | FailedModel = type_validate_json(SoloRecord, raw_records)  # type: ignore[arg-type]
            if isinstance(records, FailedModel):
                msg = f'用户Summaries数据请求错误:\n{records.error}'
                raise RequestError(msg)
            self._records[record_key] = records
            await anti_duplicate_add(
                TETRIOHistoricalData(
                    user_unique_identifier=(await self.user).unique_identifier,
                    api_type=record_key.to_records(),
                    data=records,
                    update_time=records.cache.cached_at,
                ),
            )
        return self._records[record_key]
