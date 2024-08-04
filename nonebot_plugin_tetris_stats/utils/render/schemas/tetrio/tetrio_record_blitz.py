from .tetrio_record_base import Record as BaseRecord
from .tetrio_record_base import Statistic as BaseStatistic


class Statistic(BaseStatistic):
    spp: float

    level: int


class Record(BaseRecord):
    statistic: Statistic
