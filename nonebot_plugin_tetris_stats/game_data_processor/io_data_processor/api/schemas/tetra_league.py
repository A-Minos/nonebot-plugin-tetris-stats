from pydantic import BaseModel, Field

from ..typing import Rank
from .base import FailedModel
from .base import SuccessModel as BaseSuccessModel


class _User(BaseModel):
    id: str = Field(..., alias='_id')
    username: str
    role: str
    xp: float
    supporter: bool
    verified: bool
    country: str | None = None


class _League(BaseModel):
    gamesplayed: int
    gameswon: int
    rating: float
    rank: Rank
    bestrank: Rank
    decaying: bool


class ValidLeague(_League):
    glicko: float
    rd: float
    apm: float
    pps: float
    vs: float


class ValidUser(_User):
    league: ValidLeague


class InvalidLeague(_League):
    glicko: float | None = None
    rd: float | None = None
    apm: float | None = None
    pps: float | None = None
    vs: float | None = None


class InvalidUser(_User):
    league: InvalidLeague


class Data(BaseModel):
    users: list[ValidUser | InvalidUser]


class TetraLeagueSuccess(BaseSuccessModel):
    data: Data


TetraLeague = TetraLeagueSuccess | FailedModel
