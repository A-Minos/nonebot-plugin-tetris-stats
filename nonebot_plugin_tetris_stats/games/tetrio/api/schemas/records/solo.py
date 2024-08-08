from pydantic import BaseModel

from ..base import SuccessModel
from ..base.solo import Record


class Data(BaseModel):
    entries: list[Record]


class Model(SuccessModel):
    data: Data
