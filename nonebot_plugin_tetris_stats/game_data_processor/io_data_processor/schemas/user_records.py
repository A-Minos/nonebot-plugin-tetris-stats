from datetime import datetime

from pydantic import BaseModel, Field

from .base import FailedModel
from .base import SuccessModel as BaseSuccessModel


class EndContext(BaseModel):
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
        ismulti: bool | None = None
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
        ismulti: bool | None = None
        endcontext: list[EndContext]

    record: SoloRecord | MultiRecord | None = None
    rank: int | None = None


class SuccessModel(BaseSuccessModel):
    class Data(BaseModel):
        class Records(BaseModel):
            class Sprint(BaseModeRecord): ...

            class Blitz(BaseModeRecord): ...

            sprint: Sprint = Field(..., alias='40l')
            blitz: Blitz

        class Zen(BaseModel):
            level: int
            score: int

        records: Records
        zen: Zen

    data: Data


SoloRecord = BaseModeRecord.SoloRecord
MultiRecord = BaseModeRecord.MultiRecord
UserRecords = SuccessModel | FailedModel
