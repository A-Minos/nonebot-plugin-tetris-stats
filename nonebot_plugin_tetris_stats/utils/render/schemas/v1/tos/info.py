from pydantic import BaseModel, Field

from .....typedefs import Number
from ...base import Base, People, Trending
from ..base import History


class Multiplayer(BaseModel):
    history: History
    rating: Number
    rd: Number

    lpm: Number
    pps: Number
    lpm_trending: Trending

    apm: Number
    apl: Number
    apm_trending: Trending

    adpm: Number
    vs: Number
    adpl: Number
    adpm_trending: Trending

    app: Number
    ci: Number
    dspp: Number
    or_: Number = Field(serialization_alias='or')
    ge: Number


class Singleplayer(BaseModel):
    sprint: str
    challenge: str
    marathon: str


class Info(Base):
    user: People
    multiplayer: Multiplayer
    singleplayer: Singleplayer
