from pydantic import BaseModel


class User(BaseModel):
    id: str
    username: str
    avatar_revision: int
    banner_revision: int
    country: str
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


class P(BaseModel):  # what is P
    pri: float
    sec: float
    ter: float
