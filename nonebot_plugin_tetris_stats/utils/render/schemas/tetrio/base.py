from datetime import datetime

from pydantic import BaseModel

from ....typing import Number


class TetraLeagueHistoryData(BaseModel):
    record_at: datetime
    tr: Number
