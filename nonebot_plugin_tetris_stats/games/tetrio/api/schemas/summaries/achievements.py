from typing import TypeAlias

from pydantic import BaseModel

from ..base import FailedModel, SuccessModel


class Achievement(BaseModel):
    # 这**都是些啥
    k: int
    o: int
    rt: int
    vt: int
    min: int
    deci: int
    name: str
    object: str
    category: str
    hidden: bool
    desc: str
    n: str
    stub: bool


class AchievementsSuccessModel(SuccessModel):
    data: list[Achievement]


Achievements: TypeAlias = AchievementsSuccessModel | FailedModel
