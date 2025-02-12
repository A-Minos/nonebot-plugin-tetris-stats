from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ...typedefs import Prisecter


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


class P(BaseModel):
    pri: float
    sec: float
    ter: float

    def to_prisecter(self) -> Prisecter:
        return Prisecter(f'{self.pri}:{self.sec}:{self.ter}')


# fmt: off
class ArCounts(BaseModel):
    bronze:   int | None = Field(default=None, alias='1')    # pyright: ignore [reportGeneralTypeIssues]
    silver:   int | None = Field(default=None, alias='2')    # pyright: ignore [reportGeneralTypeIssues]
    gold:     int | None = Field(default=None, alias='3')    # pyright: ignore [reportGeneralTypeIssues]
    platinum: int | None = Field(default=None, alias='4')    # pyright: ignore [reportGeneralTypeIssues]
    diamond:  int | None = Field(default=None, alias='5')    # pyright: ignore [reportGeneralTypeIssues]
    issued:   int | None = Field(default=None, alias='100')  # pyright: ignore [reportGeneralTypeIssues]
    top3:     int | None = Field(default=None, alias='t3')
    top5:     int | None = Field(default=None, alias='t5')
    top10:    int | None = Field(default=None, alias='t10')
    top25:    int | None = Field(default=None, alias='t25')
    top50:    int | None = Field(default=None, alias='t50')
    top100:   int | None = Field(default=None, alias='t100')
# fmt: on


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
