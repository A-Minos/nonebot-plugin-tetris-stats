from datetime import datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

from ..base import AggregateStats, FailedModel, Finesse, P, SuccessModel
from ..base import Clears as BaseClears
from ..base import Garbage as BaseGarbage
from .base import User


class Clears(BaseClears):
    pentas: int
    minitspintriples: int
    minitspinquads: int
    tspinpentas: int


class Garbage(BaseGarbage):
    sent_nomult: int
    maxspike: int
    maxspike_nomult: int


class _Zenith(BaseModel):
    altitude: float
    rank: float
    peakrank: float
    avgrankpts: float
    floor: int
    targetingfactor: float
    targetinggrace: float
    totalbonus: float
    revives: int
    revives_total: int = Field(..., alias='revivesTotal')
    speedrun: bool
    speedrun_seen: bool
    splits: list[int]


class Stats(BaseModel):
    lines: int
    level_lines: int
    level_lines_needed: int
    inputs: int
    holds: int
    score: int
    zenlevel: int
    zenprogress: int
    level: int
    combo: int
    topcombo: int
    combopower: int
    btb: int
    topbtb: int
    btbpower: int
    tspins: int
    piecesplaced: int
    clears: Clears
    garbage: Garbage
    kills: int
    finesse: Finesse
    zenith: _Zenith
    finaltime: float


class Results(BaseModel):
    aggregatestats: AggregateStats
    stats: Stats
    gameoverreason: str


class ExtrasZenith(BaseModel):
    mods: list[str]


class Extras(BaseModel):
    zenith: ExtrasZenith


class Record(BaseModel):
    id: str = Field(..., alias='_id')
    replayid: str
    stub: bool
    gamemode: Literal['zenith', 'zenithex']
    pb: bool
    oncepb: bool
    ts: datetime
    revolution: str | None
    user: User
    otherusers: list
    leaderboards: list[str]
    results: Results
    extras: Extras
    disputed: bool
    p: P


class Best(BaseModel):
    record: Record | None
    rank: int


class Data(BaseModel):
    record: Record | None
    rank: int
    rank_local: int
    best: Best


class ZenithSuccessModel(SuccessModel):
    data: Data


Zenith: TypeAlias = ZenithSuccessModel | FailedModel
ZenithEx: TypeAlias = ZenithSuccessModel | FailedModel
