from abc import ABC
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, PositiveInt

from .......games.tetrio.api.player import RecordType
from ....base import Base, People, TETRIOPlayer


class RecordQuery(BaseModel):
    type: RecordType
    index: PositiveInt


class User(People, TETRIOPlayer):
    country: str | None


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


class Record(Base, ABC):
    query: RecordQuery
    user: User

    replay_id: str
    global_rank: PositiveInt | None
    country_rank: PositiveInt | None
    personal_best: Literal['current', 'former'] | None
    disputed: bool

    play_at: datetime
