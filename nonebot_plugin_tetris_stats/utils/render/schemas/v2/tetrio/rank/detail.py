from datetime import datetime

from pydantic import BaseModel

from .......games.tetrio.api.typedefs import ValidRank
from ......typedefs import Number
from ....base import Base


class SpecialData(BaseModel):
    apm: Number
    pps: Number
    lpm: Number
    vs: Number
    adpm: Number
    apl: Number | None = None
    adpl: Number | None = None
    apm_holder: str | None = None
    pps_holder: str | None = None
    vs_holder: str | None = None


class Data(Base):
    name: ValidRank
    trending: Number
    require_tr: Number
    players: Number

    minimum_data: SpecialData
    average_data: SpecialData
    maximum_data: SpecialData

    updated_at: datetime
