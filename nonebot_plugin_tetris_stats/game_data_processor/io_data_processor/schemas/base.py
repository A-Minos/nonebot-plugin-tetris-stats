from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Cache(BaseModel):
    status: str
    cached_at: datetime
    cached_until: datetime


class SuccessModel(BaseModel):
    success: Literal[True]
    cache: Cache


class FailedModel(BaseModel):
    success: Literal[False]
    error: str
