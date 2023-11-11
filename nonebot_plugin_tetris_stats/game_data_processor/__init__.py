from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime

from ..utils.typing import CommandType, GameType


@dataclass
class User:
    """游戏用户"""


@dataclass
class RawResponse:
    """原始请求数据"""


@dataclass
class ProcessedData:
    """处理/验证后的数据"""


from ..utils.recorder import Recorder  # noqa: E402 避免循环导入


class Processor(ABC):
    event_id: int
    command_type: CommandType
    command_args: list[str]
    user: User
    raw_response: RawResponse
    processed_data: ProcessedData

    @abstractmethod
    def __init__(
        self,
        event_id: int,
        user: User,
        command_args: list[str],
    ) -> None:
        self.event_id = event_id
        self.user = user
        self.command_args = command_args

    @property
    @abstractmethod
    def game_platform(self) -> GameType:
        """游戏平台"""
        raise NotImplementedError

    @abstractmethod
    async def handle_bind(self, platform: str, account: str) -> str:
        """处理绑定消息"""
        raise NotImplementedError

    @abstractmethod
    async def handle_query(self) -> str:
        """处理查询消息"""
        raise NotImplementedError

    @abstractmethod
    async def generate_message(self) -> str:
        """生成消息"""
        raise NotImplementedError

    def __del__(self) -> None:
        finish_time = datetime.now(tz=UTC)
        historical_data = Recorder.get_historical_data(self.event_id)
        historical_data.game_platform = self.game_platform
        historical_data.command_type = self.command_type
        historical_data.command_args = self.command_args
        historical_data.game_user = self.user
        historical_data.processed_data = self.processed_data
        historical_data.finish_time = finish_time
        Recorder.update_historical_data(self.event_id, historical_data)


from . import (  # noqa: F401, E402
    io_data_processor,
    top_data_processor,
    tos_data_processor,
)
