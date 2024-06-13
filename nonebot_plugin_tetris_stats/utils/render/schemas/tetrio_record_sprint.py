from datetime import datetime

from pydantic import BaseModel

from ....games.tetrio.api.typing import Rank
from .base import Avatar


class TetraLeague(BaseModel):
    rank: Rank
    tr: float


class User(BaseModel):
    id: str
    name: str
    avatar: Avatar | str
    tetra_league: TetraLeague | None


class Max(BaseModel):
    combo: int
    btb: int


class Mini(BaseModel):
    total: int
    single: int
    double: int


class Tspins(BaseModel):
    total: int
    single: int
    double: int
    triple: int

    mini: Mini


class Finesse(BaseModel):
    faults: int
    accuracy: float


class Statistic(BaseModel):
    keys: int
    kpp: float
    kps: float

    max: Max

    pieces: int
    pps: float
    lines: int
    lpm: float
    holds: int | None
    score: int

    single: int
    double: int
    triple: int
    quad: int

    tspins: Tspins

    all_clear: int

    finesse: Finesse


class Record(BaseModel):
    user: User

    time: str
    rank: int | None

    statistic: Statistic

    play_at: datetime
