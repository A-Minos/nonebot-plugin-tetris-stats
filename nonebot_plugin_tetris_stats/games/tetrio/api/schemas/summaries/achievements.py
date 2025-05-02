from datetime import datetime
from enum import IntEnum
from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

from ..base import FailedModel, SuccessModel


class Rt(IntEnum):
    PERCENTILE = 1
    ISSUE = 2
    ZENITH = 3
    PERCENTILELAX = 4
    PERCENTILEVLAX = 5
    PERCENTILEMLAX = 6


class Vt(IntEnum):
    NONE = 0
    NUMBER = 1
    TIME = 2
    TIME_INV = 3
    FLOOR = 4
    ISSUE = 5
    NUMBER_INV = 6


class Art(IntEnum):
    UNRANKED = 0
    RANKED = 1
    COMPETITIVE = 2


class Rank(IntEnum):
    NONE = 0
    BRONZE = 1
    SILVER = 2
    GOLD = 3
    PLATINUM = 4
    DIAMOND = 5
    ISSUED = 100


class Ally(BaseModel):
    id: str = Field(alias='_id')
    username: str
    role: Literal['anon', 'user', 'bot', 'halfmod', 'mod', 'admin', 'sysop', 'hidden', 'banned']
    country: str | None = None
    supporter: bool
    avatar_revision: int | None = None


class X(BaseModel):
    ally: Ally | None = None


class Achievement(BaseModel):
    # 这**都是些啥
    k: int
    category: str
    name: str
    object: str
    desc: str
    o: int
    rt: Rt
    vt: Vt
    art: Art
    min: int
    deci: int
    hidden: bool
    nolb: bool
    event: str | None = None
    event_past: bool | None = None
    disabled: bool | None = None
    pair: str | None = None
    v: float | None = None
    a: float | None = None
    t: datetime | None = None
    pos: int | None = None
    total: int | None = None
    rank: Rank | None = None
    x: X | None = None
    n: str

    tiebreak: int
    notifypb: bool
    id: str | None = Field(None, alias='_id')
    progress: float | None = None
    stub: bool | None = None


class AchievementsSuccessModel(SuccessModel):
    data: list[Achievement]


Achievements: TypeAlias = AchievementsSuccessModel | FailedModel
