from typing_extensions import override

from .base import Record as BaseRecord
from .base import Statistic


class Record(BaseRecord):
    @property
    @override
    def path(self) -> str:
        return 'v2/tetrio/record/sprint'

    statistic: Statistic
    time: str
