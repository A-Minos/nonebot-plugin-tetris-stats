from ...schemas import BaseProcessedData, BaseRawResponse


class RawResponse(BaseRawResponse):
    user_profile: bytes | None = None


class ProcessedData(BaseProcessedData):
    user_profile: str | None = None
