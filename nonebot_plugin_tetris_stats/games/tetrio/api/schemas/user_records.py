from datetime import datetime

from pydantic import BaseModel, Field

from .....utils.typing import Number
from .base import FailedModel
from .base import SuccessModel as BaseSuccessModel


class Time(BaseModel):
    start: int
    zero: bool
    locked: bool
    prev: int
    frameoffset: int | None = None


class Clears(BaseModel):
    singles: int
    doubles: int
    triples: int
    quads: int
    pentas: int | None = None
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
    attack: int | None = None
    cleared: int | None = None


class Finesse(BaseModel):
    combo: int
    faults: int
    perfectpieces: int


class EndContext(BaseModel):
    seed: Number
    lines: int
    level_lines: int
    level_lines_needed: int
    inputs: int
    holds: int | None = None
    time: Time
    score: int
    zenlevel: int | None = None
    zenprogress: int | None = None
    level: int
    combo: int
    currentcombopower: int | None = None  # WTF
    topcombo: int
    btb: int
    topbtb: int
    currentbtbchainpower: int | None = None  # WTF * 2
    tspins: int
    piecesplaced: int
    clears: Clears
    garbage: Garbage
    kills: int
    finesse: Finesse
    final_time: float = Field(..., alias='finalTime')
    gametype: str


class _User(BaseModel):
    id: str = Field(..., alias='_id')
    username: str


class _Record(BaseModel):
    id: str = Field(..., alias='_id')
    stream: str
    replayid: str
    user: _User
    ts: datetime
    ismulti: bool | None = None


class SoloRecord(_Record):
    endcontext: EndContext


class MultiRecord(_Record):
    endcontext: list[EndContext]


class SoloModeRecord(BaseModel):
    record: SoloRecord | None = None
    rank: int | None = None


class Records(BaseModel):
    sprint: SoloModeRecord = Field(..., alias='40l')
    blitz: SoloModeRecord


class Zen(BaseModel):
    level: int
    score: int


class Data(BaseModel):
    records: Records
    zen: Zen


class UserRecordsSuccess(BaseSuccessModel):
    data: Data


UserRecords = UserRecordsSuccess | FailedModel
