from datetime import datetime

from pydantic import BaseModel
from typing_extensions import override

from ......games.tetrio.api.typedefs import ValidRank
from ...base import Base


class ItemData(BaseModel):
    trending: float
    require_tr: float
    players: int


class Data(Base):
    @property
    @override
    def path(self) -> str:
        return 'v1/tetrio/rank'

    items: dict[ValidRank, ItemData]
    updated_at: datetime
