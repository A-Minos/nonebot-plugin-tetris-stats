from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from ..utils.typing import GameType

T = TypeVar('T', bound=GameType)


class BaseUser(BaseModel, ABC, Generic[T]):
    """游戏用户"""

    platform: T

    def __eq__(self, other: Any) -> bool:  # noqa: ANN401
        if isinstance(other, BaseUser):
            return self.unique_identifier == other.unique_identifier
        return False

    @property
    @abstractmethod
    def unique_identifier(self) -> str:
        raise NotImplementedError
