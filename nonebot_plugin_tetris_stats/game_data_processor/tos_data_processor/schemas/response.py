from ...schemas import BaseProcessedData, BaseRawResponse
from .user_info import SuccessModel as InfoSuccess
from .user_profile import UserProfile


class RawResponse(BaseRawResponse):
    user_profile: dict[str, bytes]
    user_info: bytes | None = None


class ProcessedData(BaseProcessedData):
    user_profile: dict[str, UserProfile]
    user_info: InfoSuccess | None = None
