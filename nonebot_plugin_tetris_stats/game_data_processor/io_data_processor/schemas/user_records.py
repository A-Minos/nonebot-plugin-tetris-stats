from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EndContext(BaseModel):
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

    class Finesse(BaseModel):
        combo: int
        faults: int
        perfectpieces: int

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
    currentcombopower: int  # WTF
    topcombo: int
    btb: int
    topbtb: int
    currentbtbchainpower: int | None  # WTF * 2 40l 里有 但是 blitz 没有
    tspins: int
    piecesplaced: int
    clears: Clears
    garbage: Garbage
    kills: int
    finesse: Finesse
    final_time: float = Field(..., alias='finalTime')
    gametype: str


class BaseModeRecord(BaseModel):
    class SoloRecord(BaseModel):
        class User(BaseModel):
            id: str = Field(..., alias='_id')
            username: str

        id: str = Field(..., alias='_id')
        stream: str
        replayid: str
        user: User
        ts: datetime
        ismulti: bool | None
        endcontext: EndContext

    class MultiRecord(BaseModel):
        class User(BaseModel):
            id: str = Field(..., alias='_id')
            username: str

        id: str = Field(..., alias='_id')
        stream: str
        replayid: str
        user: User
        ts: datetime
        ismulti: bool | None
        endcontext: list[EndContext]

    record: SoloRecord | MultiRecord | None
    rank: int | None


class SuccessModel(BaseModel):
    class Cache(BaseModel):
        status: str
        cached_at: datetime
        cached_until: datetime

    class Data(BaseModel):
        class Records(BaseModel):
            class Sprint(BaseModeRecord):
                ...

            class Blitz(BaseModeRecord):
                ...

            sprint: Sprint = Field(..., alias='40l')
            blitz: Blitz

        class Zen(BaseModel):
            level: int
            score: int

        records: Records
        zen: Zen

    success: Literal[True]
    cache: Cache
    data: Data


class FailedModel(BaseModel):
    success: Literal[False]
    error: str


SoloRecord = BaseModeRecord.SoloRecord
MultiRecord = BaseModeRecord.MultiRecord
UserRecords = SuccessModel | FailedModel