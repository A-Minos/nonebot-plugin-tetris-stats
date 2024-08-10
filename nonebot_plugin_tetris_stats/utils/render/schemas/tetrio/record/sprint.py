from .base import Record as BaseRecord
from .base import Statistic


class Record(BaseRecord):
    statistic: Statistic
    time: str
