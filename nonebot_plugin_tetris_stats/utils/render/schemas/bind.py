from typing import Literal

from typing_extensions import override

from .base import Base, People


class Bind(Base):
    @property
    @override
    def path(self) -> str:
        return 'v1/binding'

    platform: Literal['TETR.IO', 'TOP', 'TOS']
    type: Literal['success', 'unknown', 'unlink', 'unverified', 'error']
    user: People
    bot: People
    prompt: str
