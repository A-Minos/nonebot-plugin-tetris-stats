from datetime import datetime

from pydantic import BaseModel

from .....typedefs import Number


class TetraLeagueHistoryData(BaseModel):
    record_at: datetime
    tr: Number
