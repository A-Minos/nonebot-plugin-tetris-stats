from pydantic import BaseModel


class User(BaseModel):
    id: str
    username: str
    avatar_revision: int | None
    banner_revision: int | None
    country: str | None
    verified: int
    supporter: int


class AggregateStats(BaseModel):
    apm: float
    pps: float
    vsscore: float


class Finesse(BaseModel):
    combo: int
    faults: int
    perfectpieces: int
