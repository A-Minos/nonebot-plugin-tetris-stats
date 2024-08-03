from pydantic import BaseModel, Field

from ..base import SuccessModel
from .base import Entry as BaseEntry


class ArCounts(BaseModel):
    bronze: int | None = Field(None, alias='1')
    silver: int | None = Field(None, alias='2')
    gold: int | None = Field(None, alias='3')
    platinum: int | None = Field(None, alias='4')
    diamond: int | None = Field(None, alias='5')
    issued: int | None = Field(None, alias='100')
    top10: int | None = Field(None, alias='t10')


class Entry(BaseEntry):
    ar: int
    ar_counts: ArCounts


class Data(BaseModel):
    entries: list[Entry]


class ArSuccessModel(SuccessModel):
    data: Data
