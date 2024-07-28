from typing import TypeAlias

from pydantic import BaseModel

from ..base import FailedModel, SuccessModel


class Data(BaseModel):
    level: int
    score: int


class ZenSuccessModel(SuccessModel):
    data: Data


Zen: TypeAlias = ZenSuccessModel | FailedModel
