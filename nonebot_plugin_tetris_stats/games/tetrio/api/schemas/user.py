from typing import Literal

from typing_extensions import override

from ....schemas import BaseUser
from ...constant import GAME_TYPE


class User(BaseUser[Literal['IO']]):
    platform: Literal['IO'] = GAME_TYPE

    ID: str
    name: str

    @property
    @override
    def unique_identifier(self) -> str:
        return self.ID
