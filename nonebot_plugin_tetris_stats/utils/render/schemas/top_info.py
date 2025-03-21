from pydantic import BaseModel

from ...typedefs import Number
from .base import People


class Data(BaseModel):
    pps: Number
    lpm: Number
    apm: Number
    apl: Number


class Info(BaseModel):
    user: People
    today: Data
    history: Data
