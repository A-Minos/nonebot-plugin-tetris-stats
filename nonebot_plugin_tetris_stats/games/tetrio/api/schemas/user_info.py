from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..typing import Rank
from .base import FailedModel
from .base import SuccessModel as BaseSuccessModel


class Badge(BaseModel):
    id: str
    label: str
    group: str | None = None
    ts: datetime | Literal[False] | None = None


class MetaLeague(BaseModel):
    decaying: bool


class NeverPlayedLeague(MetaLeague):
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
    apm: None = None
    pps: None = None
    vs: None = None


class NeverRatedLeague(MetaLeague):
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
    vs: float | None = None


class RatedLeague(MetaLeague):
    gamesplayed: int
    gameswon: int
    rating: float
    rank: Rank
    bestrank: Rank
    standing: int
    standing_local: int
    next_rank: Rank | None = None
    prev_rank: Rank | None = None
    next_at: int
    prev_at: int
    percentile: float
    percentile_rank: str
    glicko: float
    rd: float
    apm: float
    pps: float
    vs: float | None = None


class Discord(BaseModel):
    id: str
    username: str


class Connections(BaseModel):
    discord: Discord | None = None


class Distinguishment(BaseModel):
    type: str


class User(BaseModel):
    id: str = Field(..., alias='_id')
    username: str
    role: Literal['anon', 'user', 'bot', 'halfmod', 'mod', 'admin', 'sysop', 'banned']
    ts: datetime | None = None
    botmaster: str | None = None
    badges: list[Badge]
    xp: float
    gamesplayed: int
    gameswon: int
    gametime: float
    country: str | None = None
    badstanding: bool | None = None
    supporter: bool | None = None  # osk说是必有, 但实际上不是 fkosk
    supporter_tier: int
    verified: bool
    league: NeverPlayedLeague | NeverRatedLeague | RatedLeague
    avatar_revision: int | None = None
    """This user's avatar ID. Get their avatar at

    https://tetr.io/user-content/avatars/{ USERID }.jpg?rv={ AVATAR_REVISION }"""
    banner_revision: int | None = None
    """This user's banner ID. Get their banner at

    https://tetr.io/user-content/banners/{ USERID }.jpg?rv={ BANNER_REVISION }

    Ignore this field if the user is not a supporter."""
    bio: str | None = None
    connections: Connections
    friend_count: int | None = None
    distinguishment: Distinguishment | None = None


class Data(BaseModel):
    user: User


class UserInfoSuccess(BaseSuccessModel):
    data: Data


UserInfo = UserInfoSuccess | FailedModel
