from datetime import datetime

from pydantic import BaseModel

from .....games.tetrio.api.schemas.user_records import Zen
from .....games.tetrio.api.typing import Rank
from ....typing import Number
from ..base import Avatar
from .base import TetraLeagueHistoryData


class Badge(BaseModel):
    id: str
    description: str
    group: str | None
    receive_at: datetime | None


class User(BaseModel):
    id: str
    name: str
    country: str | None

    avatar: str | Avatar
    banner: str | None

    bio: str | None

    friend_count: int
    supporter_tier: int

    verified: bool
    bad_standing: bool

    badges: list[Badge]
    xp: Number

    playtime: str | None
    join_at: datetime | None


class Statistic(BaseModel):
    total: int | None
    wins: int | None


class TetraLeagueStatistic(BaseModel):
    total: int
    wins: int


class TetraLeague(BaseModel):
    rank: Rank
    highest_rank: Rank

    tr: Number

    glicko: Number
    rd: Number

    global_rank: int | None
    country_rank: int | None

    pps: Number

    apm: Number
    apl: Number

    vs: Number | None
    adpl: Number | None

    statistic: TetraLeagueStatistic

    decaying: bool

    history: list[TetraLeagueHistoryData]


class Sprint(BaseModel):
    time: str
    global_rank: int | None
    play_at: datetime


class Blitz(BaseModel):
    score: int
    global_rank: int | None
    play_at: datetime


class Info(BaseModel):
    user: User
    tetra_league: TetraLeague | None
    statistic: Statistic | None
    sprint: Sprint | None
    blitz: Blitz | None
    zen: Zen
