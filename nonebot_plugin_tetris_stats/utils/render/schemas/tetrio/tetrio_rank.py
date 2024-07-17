from datetime import datetime

from pydantic import BaseModel

from .....games.tetrio.api.typing import ValidRank


class AverageData(BaseModel):
    pps: float
    apm: float
    apl: float
    vs: float
    adpl: float


class ItemData(BaseModel):
    require_tr: float
    trending: float
    average_data: AverageData
    players: int


class Data(BaseModel):
    items: dict[ValidRank, ItemData]
    updated_at: datetime
