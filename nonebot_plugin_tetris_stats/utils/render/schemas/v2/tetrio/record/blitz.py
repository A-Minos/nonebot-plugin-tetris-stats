from .base import Record as BaseRecord
from .base import Statistic as BaseStatistic


class Statistic(BaseStatistic):
    spp: float

    level: int


class Record(BaseRecord):
    statistic: Statistic
