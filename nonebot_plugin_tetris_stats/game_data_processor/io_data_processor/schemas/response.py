from ... import ProcessedData as ProcessedDataMeta
from ... import RawResponse as RawResponseMeta
from .user_info import SuccessModel as InfoSuccess
from .user_records import SuccessModel as RecordsSuccess


class RawResponse(RawResponseMeta):
    user_info: bytes | None = None
    user_records: bytes | None = None


class ProcessedData(ProcessedDataMeta):
    user_info: InfoSuccess | None = None
    user_records: RecordsSuccess | None = None
