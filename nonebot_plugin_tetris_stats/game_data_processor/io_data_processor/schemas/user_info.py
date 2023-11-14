from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..typing import Rank
from .base import FailedModel
from .base import SuccessModel as BaseSuccessModel


class SuccessModel(BaseSuccessModel):
    class Data(BaseModel):
        class User(BaseModel):
            class Badge(BaseModel):
                id: str
                label: str
                ts: datetime | None

            class NeverPlayedLeague(BaseModel):
                gamesplayed: Literal[0]
                gameswon: Literal[0]
                rating: Literal[-1]
                rank: Literal['z']
                standing: Literal[-1]
                standing_local: Literal[-1]
                next_rank: None
                prev_rank: None
                next_at: Literal[-1]
                prev_at: Literal[-1]
                percentile: Literal[-1]
                percentile_rank: Literal['z']
                apm: None = Field(None)
                pps: None = Field(None)
                vs: None = Field(None)
                decaying: bool

            class NeverRatedLeague(BaseModel):
                gamesplayed: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]
                gameswon: int
                rating: Literal[-1]
                rank: Literal['z']
                standing: Literal[-1]
                standing_local: Literal[-1]
                next_rank: None
                prev_rank: None
                next_at: Literal[-1]
                prev_at: Literal[-1]
                percentile: Literal[-1]
                percentile_rank: Literal['z']
                apm: float
                pps: float
                vs: float
                decaying: bool

            class RatedLeague(BaseModel):
                gamesplayed: int
                gameswon: int
                rating: float
                rank: Rank
                bestrank: Rank
                standing: int
                standing_local: int
                next_rank: Rank | None
                prev_rank: Rank | None
                next_at: int
                prev_at: int
                percentile: float
                percentile_rank: str
                glicko: float
                rd: float
                apm: float
                pps: float
                vs: float | None
                decaying: bool

            class Connections(BaseModel):
                class Discord(BaseModel):
                    id: str
                    username: str

                discord: Discord | None

            class Distinguishment(BaseModel):
                type: str  # noqa: A003

            id: str = Field(..., alias='_id')
            username: str
            role: Literal['anon', 'user', 'bot', 'halfmod', 'mod', 'admin', 'sysop', 'banned']
            ts: datetime | None
            botmaster: str | None
            badges: list[Badge]
            xp: float
            gamesplayed: int
            gameswon: int
            gametime: float
            country: str | None
            badstanding: bool | None
            supporter: bool | None  # osk说是必有, 但实际上不是 fk osk
            supporter_tier: int
            verified: bool
            league: NeverPlayedLeague | NeverRatedLeague | RatedLeague
            avatar_revision: int | None
            """This user's avatar ID. Get their avatar at

            https://tetr.io/user-content/avatars/{ USERID }.jpg?rv={ AVATAR_REVISION }"""
            banner_revision: int | None
            """This user's banner ID. Get their banner at

            https://tetr.io/user-content/banners/{ USERID }.jpg?rv={ BANNER_REVISION }

            Ignore this field if the user is not a supporter."""
            bio: str | None
            connections: Connections
            friend_count: int | None
            distinguishment: Distinguishment | None

        user: User

    data: Data


NeverPlayedLeague = SuccessModel.Data.User.NeverPlayedLeague
NeverRatedLeague = SuccessModel.Data.User.NeverRatedLeague
RatedLeague = SuccessModel.Data.User.RatedLeague
UserInfo = SuccessModel | FailedModel
