from pydantic import BaseModel, Field

from ...typing import Number
from .base import People, Ranking


class Multiplayer(BaseModel):
    pps: Number
    lpm: Number
    apm: Number
    apl: Number
    vs: Number
    adpm: Number
    adpl: Number


class Radar(BaseModel):
    app: Number
    OR: Number = Field(serialization_alias='or')
    dspp: Number
    ci: Number
    ge: Number


class Info(BaseModel):
    user: People
    ranking: Ranking
    multiplayer: Multiplayer
    radar: Radar
    sprint: str
    challenge: str
    marathon: str
