from datetime import datetime

from pydantic import BaseModel

from .....games.tetrio.api.typing import Rank
from ....typing import Number
from ..base import Avatar


class TetraLeague(BaseModel):
    rank: Rank
    tr: Number

    glicko: Number | None
    rd: Number | None
    decaying: bool
    pps: Number
    apm: Number
    apl: Number
    vs: Number | None
    adpl: Number | None


class User(BaseModel):
    id: str
    name: str
    avatar: str | Avatar
    country: str | None
    verified: bool
    tetra_league: TetraLeague
    xp: Number
    join_at: datetime | None


class List(BaseModel):
    show_index: bool
    users: list[User]
