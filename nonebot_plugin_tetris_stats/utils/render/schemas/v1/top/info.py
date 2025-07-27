from pydantic import BaseModel
from typing_extensions import override

from .....typedefs import Number
from ...base import Base, People, Trending


class Data(BaseModel):
    pps: Number
    lpm: Number
    lpm_trending: Trending
    apm: Number
    apl: Number
    apm_trending: Trending


class Info(Base):
    @property
    @override
    def path(self) -> str:
        return 'v1/top/info'

    user: People
    today: Data
    historical: Data
