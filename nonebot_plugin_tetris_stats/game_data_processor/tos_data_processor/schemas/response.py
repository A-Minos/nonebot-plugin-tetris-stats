from typing import Literal

from ...schemas import BaseProcessedData, BaseRawResponse
from ..constant import GAME_TYPE
from .user_info import SuccessModel as InfoSuccess
from .user_profile import UserProfile


class RawResponse(BaseRawResponse):
    platform: Literal['TOS'] = GAME_TYPE

    user_profile: dict[str, bytes]
    user_info: bytes | None = None


class ProcessedData(BaseProcessedData):
    platform: Literal['TOS'] = GAME_TYPE

    user_profile: dict[str, UserProfile]
    user_info: InfoSuccess | None = None
