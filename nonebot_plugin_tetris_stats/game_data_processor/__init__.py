from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from nonebot.matcher import Matcher
from nonebot_plugin_alconna import AlcMatches, AlconnaMatcher

from ..utils.exception import MessageFormatError
from ..utils.recorder import Recorder
from ..utils.typing import CommandType, GameType
from .schemas import BaseProcessedData as ProcessedData
from .schemas import BaseRawResponse as RawResponse
from .schemas import BaseUser as User

UTC = timezone.utc


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
        if Recorder.is_error_event(self.event_id):
            Recorder.del_error_event(self.event_id)
            return
        historical_data = Recorder.get_historical_data(self.event_id)
        historical_data.game_platform = self.game_platform
        historical_data.command_type = self.command_type
        historical_data.command_args = self.command_args
        historical_data.game_user = self.user
        historical_data.processed_data = self.processed_data
        historical_data.finish_time = finish_time
        Recorder.update_historical_data(self.event_id, historical_data)


def add_default_handlers(matcher: type[AlconnaMatcher]) -> None:
    @matcher.handle()
    async def _(matcher: Matcher, account: MessageFormatError):
        await matcher.finish(str(account))

    @matcher.handle()
    async def _(matcher: Matcher, matches: AlcMatches):
        if matches.head_matched and matches.options != {} or matches.main_args == {}:
            await matcher.finish(
                (f'{matches.error_info!r}\n' if matches.error_info is not None else '')
                + f'输入"{matches.header_result} --help"查看帮助'
            )

    @matcher.handle()
    async def _(matcher: Matcher, other: Any):  # noqa: ANN401
        await matcher.finish()


from . import (  # noqa: F401, E402
    io_data_processor,
    top_data_processor,
    tos_data_processor,
)
