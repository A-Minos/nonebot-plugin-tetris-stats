from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from strenum import StrEnum

from ...typedefs import Lang, Number


class Base(BaseModel):
    lang: Lang


class Avatar(BaseModel):
    type: Literal['identicon']
    hash: str


class People(BaseModel):
    avatar: str | Avatar
    name: str


class Ranking(BaseModel):
    rating: Number
    rd: Number


class HistoryData(BaseModel):
    score: Number
    record_at: datetime


class Trending(StrEnum):
    UP = 'up'
    KEEP = 'keep'
    DOWN = 'down'
