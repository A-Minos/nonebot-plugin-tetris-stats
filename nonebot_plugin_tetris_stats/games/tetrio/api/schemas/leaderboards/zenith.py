from pydantic import BaseModel

from ..base import SuccessModel
from ..summaries.zenith import Record


class Data(BaseModel):
    entries: list[Record]


class ZenithSuccessModel(SuccessModel):
    data: Data
