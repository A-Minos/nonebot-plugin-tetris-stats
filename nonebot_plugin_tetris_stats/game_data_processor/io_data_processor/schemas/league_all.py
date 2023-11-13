from pydantic import BaseModel, Field

from ..typing import Rank
from .base import FailedModel
from .base import SuccessModel as BaseSuccessModel


class SuccessModel(BaseSuccessModel):
    class Data(BaseModel):
        class ValidUser(BaseModel):
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

            id: str = Field(..., alias='_id')
            username: str
            role: str
            xp: float
            league: League
            supporter: bool
            verified: bool
            country: str | None

        class InvalidUser(BaseModel):
            class League(BaseModel):
                gamesplayed: int
                gameswon: int
                rating: float
                glicko: float | None
                rd: float | None
                rank: Rank
                bestrank: Rank
                apm: float | None
                pps: float | None
                vs: float | None
                decaying: bool

            id: str = Field(..., alias='_id')
            username: str
            role: str
            xp: float
            league: League
            supporter: bool
            verified: bool
            country: str | None

        users: list[ValidUser | InvalidUser]

    data: Data


LeagueAll = SuccessModel | FailedModel
ValidUser = SuccessModel.Data.ValidUser
InvalidUser = SuccessModel.Data.InvalidUser
