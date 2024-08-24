from pydantic import BaseModel

from ..base import FailedModel, SuccessModel
from ..summaries.solo import Record


class Data(BaseModel):
    entries: list[Record]


class SoloSuccessModel(SuccessModel):
    data: Data


Solo = SoloSuccessModel | FailedModel
