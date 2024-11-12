from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..base import P
from . import AggregateStats, Clears, Finesse, Garbage


class Time(BaseModel):
    start: int
    zero: bool
    locked: bool
    prev: int
    frameoffset: int | None = None


class Stats(BaseModel):
    seed: float | None = None  # ?: 不知道是之后都没有了还是还会有
    lines: int
    level_lines: int
    level_lines_needed: int
    inputs: int
    holds: int = 0
    time: Time | None = None  # ?: 不知道是之后都没有了还是还会有
    score: int
    zenlevel: int | None = None
    zenprogress: int | None = None
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
    otherusers: list
    leaderboards: list[str]
    results: Results
    extras: dict
    disputed: bool
    p: P
