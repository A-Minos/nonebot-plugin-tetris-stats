from datetime import datetime

from pydantic import BaseModel

from .tetrio_record_base import RecordStatistic as Statistic
from .tetrio_record_base import User


class Record(BaseModel):
    user: User

    time: str
    replay_id: str
    rank: int | None

    statistic: Statistic

    play_at: datetime
