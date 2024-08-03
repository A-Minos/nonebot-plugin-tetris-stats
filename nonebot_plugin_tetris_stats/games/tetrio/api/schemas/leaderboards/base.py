from datetime import datetime

from pydantic import BaseModel, Field

from ...typing import Rank
from ..base import P


class League(BaseModel):
    gamesplayed: int
    gameswon: int
    rating: int
    rank: Rank
    decaying: bool


class Entry(BaseModel):
    id: str = Field(..., alias='_id')
    username: str
    role: str
    xp: float
    league: League
    supporter: bool | None = None
    verified: bool
    country: str | None = None
    ts: datetime
    gamesplayed: int
    gameswon: int
    gametime: float
    p: P
