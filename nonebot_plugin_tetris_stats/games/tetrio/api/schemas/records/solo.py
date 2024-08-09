from typing import TypeAlias

from pydantic import BaseModel

from ..base import FailedModel, SuccessModel
from ..base.solo import Record


class Data(BaseModel):
    entries: list[Record]


class SoloSuccessModel(SuccessModel):
    data: Data


Solo: TypeAlias = SoloSuccessModel | FailedModel
