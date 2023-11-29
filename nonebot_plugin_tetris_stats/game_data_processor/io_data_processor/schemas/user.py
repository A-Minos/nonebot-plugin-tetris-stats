from typing import Literal

from ...schemas import BaseUser
from ..constant import GAME_TYPE


class User(BaseUser):
    platform: Literal['IO'] = GAME_TYPE

    ID: str | None = None
    name: str | None = None

    @property
    def unique_identifier(self) -> str:
        if self.ID is None:
            raise ValueError('不完整的User!')
        return self.ID
