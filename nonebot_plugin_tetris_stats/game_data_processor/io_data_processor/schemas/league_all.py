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


class SuccessModel(BaseSuccessModel):
    class Data(BaseModel):
        class ValidUser(_User):
            class League(BaseModel):
                gamesplayed: int
                gameswon: int
                rating: float
                glicko: float
                rd: float
                rank: Rank
                bestrank: Rank
                apm: float
                pps: float
                vs: float
                decaying: bool

            league: League

        class InvalidUser(_User):
            class League(BaseModel):
                gamesplayed: int
                gameswon: int
                rating: float
                glicko: float | None = None
                rd: float | None = None
                rank: Rank
                bestrank: Rank
                apm: float | None = None
                pps: float | None = None
                vs: float | None = None
                decaying: bool

            league: League

        users: list[ValidUser | InvalidUser]

    data: Data


LeagueAll = SuccessModel | FailedModel
ValidUser = SuccessModel.Data.ValidUser
InvalidUser = SuccessModel.Data.InvalidUser
