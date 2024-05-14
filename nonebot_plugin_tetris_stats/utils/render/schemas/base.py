from typing import Literal

from pydantic import BaseModel


class Avatar(BaseModel):
    type: Literal['identicon']
    hash: str


class People(BaseModel):
    avatar: str | Avatar
    name: str
