from datetime import datetime

from pydantic import BaseModel

from .....games.tetrio.api.typing import ValidRank


class SpecialData(BaseModel):
    apm: float
    pps: float
    lpm: float
    vs: float
    adpm: float
    apl: float | None = None
    adpl: float | None = None
    apm_holder: str | None = None
    pps_holder: str | None = None
    vs_holder: str | None = None


class Data(BaseModel):
    name: ValidRank
    trending: float
    require_tr: float
    players: int

    minimum_data: SpecialData
    average_data: SpecialData
    maximum_data: SpecialData

    updated_at: datetime
