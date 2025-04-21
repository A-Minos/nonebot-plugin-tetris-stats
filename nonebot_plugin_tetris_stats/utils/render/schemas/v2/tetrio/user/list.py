from pydantic import BaseModel

from .......games.tetrio.api.typedefs import Rank
from ......typedefs import Number
from ....base import Avatar, Base


class TetraLeague(BaseModel):
    pps: Number
    apm: Number
    apl: Number
    vs: Number | None
    adpl: Number | None

    rank: Rank
    tr: Number

    glicko: Number | None
    rd: Number | None
    decaying: bool


class User(BaseModel):
    id: str
    name: str
    avatar: str | Avatar
    country: str | None
    xp: Number


class Data(BaseModel):
    user: User
    tetra_league: TetraLeague


class List(Base):
    show_index: bool
    data: list[Data]
