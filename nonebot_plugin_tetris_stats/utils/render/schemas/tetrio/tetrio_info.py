from pydantic import BaseModel

from .....games.tetrio.api.typing import Rank
from ....typing import Number
from ..base import People, Ranking
from .base import TetraLeagueHistoryData


class User(People):
    bio: str | None


class TetraLeague(BaseModel):
    rank: Rank
    tr: Number
    global_rank: Number
    pps: Number
    lpm: Number
    apm: Number
    apl: Number
    vs: Number
    adpm: Number
    adpl: Number


class TetraLeagueHistory(BaseModel):
    data: list[TetraLeagueHistoryData]
    split_interval: Number
    min_tr: Number
    max_tr: Number
    offset: Number


class Radar(BaseModel):
    app: Number
    dsps: Number
    dspp: Number
    ci: Number
    ge: Number


class Info(BaseModel):
    user: User
    ranking: Ranking
    tetra_league: TetraLeague
    tetra_league_history: TetraLeagueHistory
    radar: Radar
    sprint: str
    blitz: str
