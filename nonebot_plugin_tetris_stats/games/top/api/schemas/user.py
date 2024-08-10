from typing import Literal

from typing_extensions import override

from ....schemas import BaseUser
from ...constant import GAME_TYPE


class User(BaseUser[Literal['TOP']]):
    platform: Literal['TOP'] = GAME_TYPE

    user_name: str

    @property
    @override
    def unique_identifier(self) -> str:
        return self.user_name
