from abc import ABC
from datetime import datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel

from ....base import Base, People

RecordRenderType: TypeAlias = Literal['best', 'personal_best', 'recent', 'disputed']


class User(People):
    id: str


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
    type: RecordRenderType

    user: User

    replay_id: str
    rank: int | None
    personal_rank: int | None

    play_at: datetime
