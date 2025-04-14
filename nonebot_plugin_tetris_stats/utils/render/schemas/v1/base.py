from pydantic import BaseModel

from ....typedefs import Number
from ..base import HistoryData


class History(BaseModel):
    data: list[HistoryData]
    split_interval: Number
    min_tr: Number
    max_tr: Number
    offset: Number
