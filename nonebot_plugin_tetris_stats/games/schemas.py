from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from ..utils.typedefs import GameType

T = TypeVar('T', bound=GameType)


class BaseUser(BaseModel, ABC, Generic[T]):
    """游戏用户"""

    platform: T

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BaseUser):
            return self.unique_identifier == other.unique_identifier
        return False

    @property
    @abstractmethod
    def unique_identifier(self) -> str:
        raise NotImplementedError
