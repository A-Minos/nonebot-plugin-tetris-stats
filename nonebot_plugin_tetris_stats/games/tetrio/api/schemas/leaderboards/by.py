from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ...typedefs import Rank, ValidRank
from ..base import ArCounts, FailedModel, P, SuccessModel


class BaseLeague(BaseModel):
    gamesplayed: int
    gameswon: int
    tr: float
    gxe: float
    rank: Rank
    bestrank: ValidRank
    glicko: float
    rd: float
    decaying: bool


class InvalidLeague(BaseLeague):
    pps: float | None
    apm: None
    vs: None


class League(BaseLeague):
    pps: float
    apm: float
    vs: float


class BaseEntry(BaseModel):
    id: str = Field(..., alias='_id')
    username: str
    role: Literal['anon', 'user', 'bot', 'halfmod', 'mod', 'admin', 'sysop']
    ts: datetime | None = None
    xp: float
    country: str | None = None
    supporter: bool | None = None
    gamesplayed: int
    gameswon: int
    gametime: float
    ar: int
    ar_counts: ArCounts
    p: P


class InvalidEntry(BaseEntry):
    league: InvalidLeague


class Entry(BaseEntry):
    league: League


class Data(BaseModel):
    entries: list[Entry | InvalidEntry]


class BySuccessModel(SuccessModel):
    data: Data


By = BySuccessModel | FailedModel
