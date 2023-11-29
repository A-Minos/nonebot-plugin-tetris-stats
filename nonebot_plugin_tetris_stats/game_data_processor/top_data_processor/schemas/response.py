from typing import Literal

from ...schemas import BaseProcessedData, BaseRawResponse
from ..constant import GAME_TYPE


class RawResponse(BaseRawResponse):
    platform: Literal['TOP'] = GAME_TYPE

    user_profile: bytes | None = None


class ProcessedData(BaseProcessedData):
    platform: Literal['TOP'] = GAME_TYPE

    user_profile: str | None = None
