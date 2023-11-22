from abc import ABC, abstractmethod

from pydantic import BaseModel


class BaseUser(ABC, BaseModel):
    """游戏用户"""

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, BaseUser):
            return self.unique_identifier == __value.unique_identifier
        return False

    @property
    @abstractmethod
    def unique_identifier(self) -> str:
        raise NotImplementedError


class BaseRawResponse(BaseModel):
    """原始请求数据"""


class BaseProcessedData(BaseModel):
    """处理/验证后的数据"""
