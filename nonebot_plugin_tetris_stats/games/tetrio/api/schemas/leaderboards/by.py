from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ...typing import Rank, ValidRank
from ..base import FailedModel, P, SuccessModel


class ArCounts(BaseModel):
    bronze: int | None = Field(default=None, alias='1')
    silver: int | None = Field(default=None, alias='2')
    gold: int | None = Field(default=None, alias='3')
    platinum: int | None = Field(default=None, alias='4')
    diamond: int | None = Field(default=None, alias='5')
    issued: int | None = Field(default=None, alias='100')
    top3: int | None = Field(default=None, alias='t3')
    top5: int | None = Field(default=None, alias='t5')
    top10: int | None = Field(default=None, alias='t10')
    top25: int | None = Field(default=None, alias='t25')
    top50: int | None = Field(default=None, alias='t50')
    top100: int | None = Field(default=None, alias='t100')


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
