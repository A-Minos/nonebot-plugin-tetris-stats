from abc import ABC, abstractmethod

from pydantic import BaseModel

from ..utils.typing import GameType


class Base(BaseModel):
    platform: GameType


class BaseUser(ABC, Base):
    """游戏用户"""

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, BaseUser):
            return self.unique_identifier == __value.unique_identifier
        return False

    @property
    @abstractmethod
    def unique_identifier(self) -> str:
        raise NotImplementedError
