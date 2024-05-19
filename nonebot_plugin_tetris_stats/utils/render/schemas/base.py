from typing import Literal

from pydantic import BaseModel

from ...typing import Number


class Avatar(BaseModel):
    type: Literal['identicon']
    hash: str


class People(BaseModel):
    avatar: str | Avatar
    name: str


class Ranking(BaseModel):
    rating: Number
    rd: Number
