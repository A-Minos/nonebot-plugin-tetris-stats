from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from strenum import StrEnum

from ...typedefs import Lang, Number


class Base(BaseModel, ABC):
    @property
    @abstractmethod
    def path(self) -> str:
        raise NotImplementedError

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

    @classmethod
    def compare(cls, old: float, new: float) -> 'Trending':
        if old > new:
            return cls.DOWN
        if old < new:
            return cls.UP
        return cls.KEEP
