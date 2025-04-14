from pydantic import BaseModel, Field

from .....typedefs import Number
from ...base import People, Trending
from ..base import History


class Multiplayer(BaseModel):
    history: History

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


class Info(BaseModel):
    user: People
    multiplayer: Multiplayer
    singleplayer: Singleplayer
