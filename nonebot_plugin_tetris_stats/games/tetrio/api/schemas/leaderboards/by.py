from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ...typing import Rank, ValidRank
from ..base import ArCounts, FailedModel, P, SuccessModel


class League(BaseModel):
    gamesplayed: int
    gameswon: int
    tr: float
    gxe: float
    rank: Rank
    bestrank: ValidRank
    glicko: float
    rd: float
    apm: float
    pps: float
    vs: float
    decaying: bool


class Entry(BaseModel):
    id: str = Field(..., alias='_id')
    username: str
    role: Literal['anon', 'user', 'bot', 'halfmod', 'mod', 'admin', 'sysop']
    ts: datetime | None = None
    xp: float
    country: str | None = None
    supporter: bool | None = None
    league: League
    gamesplayed: int
    gameswon: int
    gametime: float
    ar: int
    ar_counts: ArCounts
    p: P


class Data(BaseModel):
    entries: list[Entry]


class BySuccessModel(SuccessModel):
    data: Data


By = BySuccessModel | FailedModel
