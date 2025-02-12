from typing import Literal

from nonebot.compat import PYDANTIC_V2
from pydantic import BaseModel, Field

from ...typedefs import Rank, S1Rank, S1ValidRank
from ..base import SuccessModel

if PYDANTIC_V2:
    from pydantic import field_validator
else:
    from pydantic import validator


class PastInner(BaseModel):
    season: str
    username: str
    country: str | None = None
    placement: int | None = None
    gamesplayed: int
    gameswon: int
    glicko: float
    gxe: float
    tr: float
    rd: float
    rank: S1Rank
    bestrank: S1ValidRank
    ranked: bool
    apm: float
    pps: float
    vs: float


class Past(BaseModel):
    first: PastInner | None = Field(default=None, alias='1')  # pyright: ignore [reportGeneralTypeIssues]


class BaseData(BaseModel):
    decaying: bool
    past: Past


class NeverPlayedData(BaseData):
    gamesplayed: Literal[0]
    gameswon: Literal[0]
    glicko: Literal[-1]
    rd: Literal[-1]
    gxe: Literal[-1]
    tr: Literal[-1]
    rank: Literal['z']
    apm: None = None
    pps: None = None
    vs: None = None
    standing: Literal[-1]
    standing_local: Literal[-1]
    prev_rank: None
    prev_at: Literal[-1]
    next_rank: None
    next_at: Literal[-1]
    percentile: Literal[-1]
    percentile_rank: Literal['z']


class NeverRatedData(BaseData):
    gamesplayed: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]
    gameswon: int
    glicko: Literal[-1]
    rd: Literal[-1]
    gxe: Literal[-1]
    tr: Literal[-1]
    apm: float
    pps: float
    vs: float
    rank: Literal['z']
    standing: Literal[-1]
    standing_local: Literal[-1]
    prev_rank: None
    prev_at: Literal[-1]
    next_rank: None
    next_at: Literal[-1]
    percentile: Literal[-1]
    percentile_rank: Literal['z']

    if PYDANTIC_V2:

        @field_validator('apm', 'pps', 'vs', mode='before')
        @classmethod
        def _(cls, value: float | None) -> float:
            if value is None:
                return 0
            return value

    else:

        @validator('apm', 'pps', 'vs', pre=True, always=True)
        @classmethod
        def _(cls, value: float | None) -> float:
            if value is None:
                return 0
            return value


class RatedData(BaseData):
    gamesplayed: int
    gameswon: int
    glicko: float
    rd: float
    gxe: float
    tr: float
    rank: Rank
    bestrank: Rank
    standing: int
    apm: float
    pps: float
    vs: float
    standing_local: int
    prev_rank: Rank | None = None
    prev_at: int
    next_rank: Rank | None = None
    next_at: int
    percentile: float
    percentile_rank: str


class InvalidData(BaseModel):
    """I don't know what osk is doing, but the return value is an empty dictionary"""


class LeagueSuccessModel(SuccessModel):
    data: NeverPlayedData | NeverRatedData | RatedData | InvalidData
