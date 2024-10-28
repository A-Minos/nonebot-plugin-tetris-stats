from datetime import datetime
from enum import IntEnum
from typing import Literal, NamedTuple

from pydantic import BaseModel, Field

from ..base import FailedModel
from ..base import SuccessModel as BaseSuccessModel


class Result(IntEnum):
    VICTORY = 1
    DEFEAT = 2
    VICTORY_BY_DISQUALIFICATION = 3
    DEFEAT_BY_DISQUALIFICATION = 4
    TIE = 5
    NO_CONTEST = 6
    MATCH_NULLIFIED = 7


class Point(NamedTuple):
    timestamp_offset: int
    result: Result
    post_match_tr: int
    opponent_pre_match_tr: int
    """If the opponent was unranked, same as post_match_tr."""


class Data(BaseModel):
    start_time: datetime = Field(..., alias='startTime')
    points: list[Point] = Field(..., min_length=1)


class Empty(BaseModel):
    start_time: Literal[9007199254740991] = Field(..., alias='startTime')
    points: list = Field(..., max_length=0)


class LeagueFlowSuccess(BaseSuccessModel):
    data: Data | Empty


LeagueFlow = LeagueFlowSuccess | FailedModel
