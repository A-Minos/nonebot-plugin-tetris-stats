from datetime import datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

from ..base import FailedModel, SuccessModel
from .base import AggregateStats, Finesse, P, User


class Time(BaseModel):
    start: int
    zero: bool
    locked: bool
    prev: int
    frameoffset: int


class Clears(BaseModel):
    singles: int
    doubles: int
    triples: int
    quads: int
    realtspins: int
    minitspins: int
    minitspinsingles: int
    tspinsingles: int
    minitspindoubles: int
    tspindoubles: int
    tspintriples: int
    tspinquads: int
    allclear: int


class Garbage(BaseModel):
    sent: int
    received: int
    attack: int
    cleared: int


class Stats(BaseModel):
    seed: int
    lines: int
    level_lines: int
    level_lines_needed: int
    inputs: int
    holds: int
    time: Time
    score: int
    zenlevel: int
    zenprogress: int
    level: int
    combo: int
    currentcombopower: int | None = None
    topcombo: int
    btb: int
    topbtb: int
    currentbtbchainpower: int | None = None
    tspins: int
    piecesplaced: int
    clears: Clears
    garbage: Garbage
    kills: int
    finesse: Finesse
    finaltime: float


class Results(BaseModel):
    aggregatestats: AggregateStats
    stats: Stats
    gameoverreason: str


class Record(BaseModel):
    id: str = Field(..., alias='_id')
    replayid: str
    stub: bool
    gamemode: Literal['40l', 'blitz']
    pb: bool
    oncepb: bool
    ts: datetime
    revolution: None
    user: User
    otherusers: list
    leaderboards: list[str]
    results: Results
    extras: dict
    disputed: bool
    p: P


class Data(BaseModel):
    record: Record | None
    rank: int
    rank_local: int


class SoloSuccessModel(SuccessModel):
    data: Data


Sprint: TypeAlias = SoloSuccessModel | FailedModel
Blitz: TypeAlias = SoloSuccessModel | FailedModel
