from pydantic import BaseModel

from ..base import SuccessModel
from ..summaries.solo import Record


class Data(BaseModel):
    entries: list[Record]


class SoloSuccessModel(SuccessModel):
    data: Data
