from datetime import datetime

from pydantic import BaseModel

from .......games.tetrio.api.typedefs import ValidRank
from ......typedefs import Number
from ....base import Base


class AverageData(BaseModel):
    pps: Number
    apm: Number
    apl: Number
    vs: Number
    adpl: Number


class ItemData(BaseModel):
    require_tr: Number
    trending: Number
    average_data: AverageData
    players: Number


class Data(Base):
    items: dict[ValidRank, ItemData]
    updated_at: datetime
