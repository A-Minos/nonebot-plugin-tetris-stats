from pydantic import BaseModel

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
    user: People
    today: Data
    historical: Data
