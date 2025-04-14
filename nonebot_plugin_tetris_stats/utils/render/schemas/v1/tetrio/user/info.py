from pydantic import BaseModel

from .......games.tetrio.api.typedefs import Rank
from ......typedefs import Number
from ....base import Base, People, Trending
from ...base import History


class User(People):
    bio: str | None


class Multiplayer(BaseModel):
    glicko: str
    rd: Number
    rank: Rank
    tr: str
    global_rank: Number

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
    dsps: Number
    ge: Number


class Singleplayer(BaseModel):
    sprint: str
    blitz: str


class Info(Base):
    user: User
    multiplayer: Multiplayer
    singleplayer: Singleplayer
