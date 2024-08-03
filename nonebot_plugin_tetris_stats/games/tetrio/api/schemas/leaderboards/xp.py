from pydantic import BaseModel

from ..base import SuccessModel
from .base import Entry


class Data(BaseModel):
    entries: list[Entry]


class XpSuccessModel(SuccessModel):
    data: Data
