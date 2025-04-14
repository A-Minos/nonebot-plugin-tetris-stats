from typing import Literal

from .base import Base, People


class Bind(Base):
    platform: Literal['TETR.IO', 'TOP', 'TOS']
    type: Literal['success', 'unknown', 'unlink', 'unverified', 'error']
    user: People
    bot: People
    prompt: str
