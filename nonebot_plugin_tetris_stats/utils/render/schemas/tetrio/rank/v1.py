from datetime import datetime

from pydantic import BaseModel

from ......games.tetrio.api.typedefs import ValidRank


class ItemData(BaseModel):
    trending: float
    require_tr: float
    players: int


class Data(BaseModel):
    items: dict[ValidRank, ItemData]
    updated_at: datetime
