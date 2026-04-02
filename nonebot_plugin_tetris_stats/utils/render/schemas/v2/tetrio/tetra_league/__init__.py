from datetime import datetime

from pydantic import BaseModel
from typing_extensions import override

from ....base import Avatar, Base


class Stats(BaseModel):
    pps: float
    apm: float
    vs: float


class Player(BaseModel):
    id: str
    name: str
    avatar: str | Avatar
    country: str | None
    stats: Stats


class Score(BaseModel):
    user: int
    opponent: int


class Match(BaseModel):
    sequence: int
    replay_id: str
    played_at: datetime
    user: Player
    opponent: Player
    is_winner: bool
    score: Score


class Data(Base):
    @property
    @override
    def path(self) -> str:
        return 'v2/tetrio/tetra-league'

    matches: list[Match]
