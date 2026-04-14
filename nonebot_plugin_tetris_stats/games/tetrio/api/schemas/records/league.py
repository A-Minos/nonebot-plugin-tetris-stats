from datetime import datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

from ..base import FailedModel, P, SuccessModel


class OtherUser(BaseModel):
    id: str
    username: str
    avatar_revision: int | None = None
    banner_revision: int | None = None
    country: str | None = None
    supporter: bool | None = None


class Stats(BaseModel):
    apm: float
    pps: float
    vsscore: float
    garbagesent: int
    garbagereceived: int
    kills: int
    altitude: int
    rank: int
    targetingfactor: int
    targetinggrace: int
    btb: int
    revives: int
    escapeartist: int | None = None
    blockrationing_app: int | None = None
    blockrationing_final: int | None = None


class Leaderboard(BaseModel):
    id: str
    username: str
    active: bool
    naturalorder: int
    shadows: list[str]
    shadowed_by: list[str | None] = Field(alias='shadowedBy')
    wins: int
    stats: Stats


class Round(BaseModel):
    id: str
    username: str
    active: bool
    naturalorder: int
    shadows: list[str]
    shadowed_by: list[str | None] = Field(alias='shadowedBy')
    alive: bool
    lifetime: int
    stats: Stats


class Results(BaseModel):
    leaderboard: list[Leaderboard]
    rounds: list[list[Round]]


class Snapshot(BaseModel):
    glicko: float
    rd: float
    tr: float
    rank: str
    placement: int


class Extras(BaseModel):
    league: dict[str, list[Snapshot]]
    result: str


class Record(BaseModel):
    id: str = Field(alias='_id')
    replayid: str
    stub: bool
    gamemode: Literal['league']
    pb: bool
    oncepb: bool
    ts: datetime
    revolution: None = None
    otherusers: list[OtherUser]
    leaderboards: list[str]
    results: Results
    extras: Extras
    disputed: bool
    p: P


class Data(BaseModel):
    entries: list[Record]


class LeagueSuccessModel(SuccessModel):
    data: Data


League: TypeAlias = LeagueSuccessModel | FailedModel
