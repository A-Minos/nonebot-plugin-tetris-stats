from typing_extensions import override

from .base import Record as BaseRecord
from .base import Statistic as BaseStatistic


class Statistic(BaseStatistic):
    spp: float

    level: int


class Record(BaseRecord):
    @property
    @override
    def path(self) -> str:
        return 'v2/tetrio/record/blitz'

    statistic: Statistic
