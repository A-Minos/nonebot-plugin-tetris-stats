from datetime import datetime

from pydantic import BaseModel

from ......games.tetrio.api.typedefs import ValidRank
from ...base import Base


class ItemData(BaseModel):
    trending: float
    require_tr: float
    players: int


class Data(Base):
    items: dict[ValidRank, ItemData]
    updated_at: datetime
