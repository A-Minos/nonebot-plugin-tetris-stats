from datetime import datetime

from pydantic import BaseModel

from .tetrio_record_base import RecordStatistic, User


class Statistic(RecordStatistic):
    spp: float

    level: int


class Record(BaseModel):
    user: User

    replay_id: str
    rank: int | None

    statistic: Statistic

    play_at: datetime
