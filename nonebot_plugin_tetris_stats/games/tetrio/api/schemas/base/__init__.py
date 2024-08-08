from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AggregateStats(BaseModel):
    apm: float
    pps: float
    vsscore: float


class Finesse(BaseModel):
    combo: int
    faults: int
    perfectpieces: int


class Clears(BaseModel):
    singles: int
    doubles: int
    triples: int
    quads: int
    realtspins: int
    minitspins: int
    minitspinsingles: int
    tspinsingles: int
    minitspindoubles: int
    tspindoubles: int
    tspintriples: int
    tspinquads: int
    allclear: int


class Garbage(BaseModel):
    sent: int
    received: int
    attack: int | None
    cleared: int


class P(BaseModel):  # what is P
    pri: float
    sec: float
    ter: float


class Cache(BaseModel):
    status: str
    cached_at: datetime
    cached_until: datetime


class SuccessModel(BaseModel):
    success: Literal[True]
    cache: Cache


class FailedModel(BaseModel):
    success: Literal[False]
    error: str
