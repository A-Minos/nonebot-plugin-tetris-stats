from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .......games.tetrio.api.schemas.summaries.achievements import ArType, RankType
from .......games.tetrio.api.schemas.summaries.achievements import Rank as AchievementRank
from .......games.tetrio.api.typedefs import Rank
from ......typedefs import Number
from ....base import Avatar, Base, HistoryData


class Badge(BaseModel):
    id: str
    description: str
    group: str | None
    receive_at: datetime | None


class Achievement(BaseModel):
    key: int
    rank_type: RankType
    ar_type: ArType
    stub: bool | None
    rank: AchievementRank | None
    achieved_score: float | None
    pos: int | None
    progress: float | None
    total: int | None


class User(BaseModel):
    id: str
    name: str
    country: str | None

    role: Literal['anon', 'user', 'bot', 'halfmod', 'mod', 'admin', 'sysop', 'hidden', 'banned']
    botmaster: str | None

    avatar: str | Avatar
    banner: str | None

    bio: str | None

    friend_count: int | None
    supporter_tier: int

    bad_standing: bool

    badges: list[Badge]
    xp: Number

    ar: Number
    achievements: list[Achievement]

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

    glicko: Number | None
    rd: Number | None

    global_rank: int | None
    country_rank: int | None

    pps: Number | None

    apm: Number | None
    apl: Number | None

    vs: Number | None
    adpl: Number | None

    statistic: TetraLeagueStatistic

    decaying: bool

    history: list[HistoryData] | None


class Sprint(BaseModel):
    time: str
    global_rank: Number | None
    country_rank: Number | None
    play_at: datetime


class Blitz(BaseModel):
    score: Number
    global_rank: int | None
    country_rank: int | None
    play_at: datetime


class Zen(BaseModel):
    level: int
    score: int


class Week(BaseModel):
    altitude: Number
    global_rank: int | None
    country_rank: int | None
    play_at: datetime


class Best(BaseModel):
    altitude: Number
    global_rank: int | None
    play_at: datetime


class Zenith(BaseModel):
    week: Week | None
    best: Best | None


class Info(Base):
    user: User
    tetra_league: TetraLeague | None
    zenith: Zenith | None
    zenithex: Zenith | None
    statistic: Statistic | None
    sprint: Sprint | None
    blitz: Blitz | None
    zen: Zen | None
