from pydantic import BaseModel, Field

from ...typing import Rank, S1Rank, S1ValidRank, ValidRank
from ..base import SuccessModel


class PastInner(BaseModel):
    season: str
    username: str
    country: str
    placement: int
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
    first: PastInner = Field(..., alias='1')


class Data(BaseModel):
    gamesplayed: int
    gameswon: int
    glicko: float
    rd: float
    gxe: float
    tr: float
    rank: Rank
    bestrank: Rank = Field('z')
    apm: float
    pps: float
    vs: float
    decaying: bool
    standing: int
    standing_local: int
    prev_rank: ValidRank | None = None
    prev_at: int
    next_rank: ValidRank | None = None
    next_at: int
    percentile: float
    percentile_rank: Rank
    past: Past


class LeagueSuccessModel(SuccessModel):
    data: Data
