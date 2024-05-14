from typing import Literal

from pydantic import BaseModel

from .base import People


class Bind(BaseModel):
    platform: Literal['TETR.IO', 'TOP', 'TOS']
    status: Literal['error', 'success', 'unknown', 'unlink', 'unverified']
    user: People
    bot: People
    command: str
