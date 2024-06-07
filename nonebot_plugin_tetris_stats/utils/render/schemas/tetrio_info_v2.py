from datetime import datetime

from pydantic import BaseModel

from ....games.tetrio.api.typing import Rank
from ...typing import Number
from .base import Avatar


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

    badges: list[str]
    xp: Number

    playtime: str
    join_at: datetime | None


class Statistic(BaseModel):
    total: int
    wins: int


class TetraLeague(BaseModel):
    rank: Rank
    highest_rank: Rank

    tr: Number

    glicko: Number
    rd: Number

    global_rank: int
    country_rank: int

    pps: Number

    apm: Number
    adpm: Number

    vs: Number
    adpl: Number

    statistic: Statistic


class Sprint(BaseModel):
    time: str
    global_rank: int | None
    play_at: datetime


class Blitz(BaseModel):
    score: int
    global_rank: int | None
    play_at: datetime


class Zen(BaseModel):
    score: int
    level: int


class Info(BaseModel):
    user: User
    tetra_league: TetraLeague | None
    statistic: Statistic | None
    sprint: Sprint | None
    blitz: Blitz | None
    zen: Zen
