from datetime import datetime

from pydantic import BaseModel

from .....typedefs import Number
from ...base import Base


class StatisticalData(BaseModel):
    pps: Number
    apm: Number
    apl: Number
    vs: Number
    adpl: Number


class User(BaseModel):
    id: str
    name: str


class Handling(BaseModel):
    arr: Number
    das: Number
    sdf: Number


class Game(BaseModel):
    user: User
    points: Number
    average_data: StatisticalData
    data: list[StatisticalData]
    handling: Handling


class Data(Base):
    replay_id: str
    games: list[Game]
    play_at: datetime
