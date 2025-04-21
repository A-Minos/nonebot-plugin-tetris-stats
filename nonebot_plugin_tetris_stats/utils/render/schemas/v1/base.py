from pydantic import BaseModel

from ....typedefs import Number
from ..base import HistoryData


class History(BaseModel):
    data: list[HistoryData]
    split_interval: Number
    min_value: Number
    max_value: Number
    offset: Number
