from datetime import datetime
from typing import Any

from nonebot.adapters import Message
from nonebot_plugin_orm import Model
from pydantic import BaseModel
from sqlalchemy import JSON, DateTime, Dialect, PickleType, String, TypeDecorator
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from ..game_data_processor.schemas import BaseProcessedData, BaseUser
from ..utils.typing import CommandType, GameType


class PydanticType(TypeDecorator):
    impl = JSON

    def process_bind_param(self, value: Any | None, dialect: Dialect) -> str:  # noqa: ANN401
        # 将 Pydantic 模型实例转换为 JSON
        if isinstance(value, BaseModel):
            return value.json()
        raise TypeError

    def process_result_value(self, value: Any | None, dialect: Dialect) -> BaseModel:  # noqa: ANN401
        # 将 JSON 转换回 Pydantic 模型实例
        if isinstance(value, str | bytes):
            return BaseModel.parse_raw(value)
        raise TypeError


class Bind(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    chat_platform: Mapped[str] = mapped_column(String(32), index=True)
    chat_account: Mapped[str] = mapped_column(index=True)
    game_platform: Mapped[GameType] = mapped_column(String(32))
    game_account: Mapped[str]


class HistoricalData(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    trigger_time: Mapped[datetime] = mapped_column(DateTime)
    bot_platform: Mapped[str | None] = mapped_column(String(32))
    bot_account: Mapped[str | None]
    source_type: Mapped[str | None] = mapped_column(String(32), index=True)
    source_account: Mapped[str | None] = mapped_column(index=True)
    message: Mapped[Message | None] = mapped_column(PickleType)
    game_platform: Mapped[GameType] = mapped_column(String(32), index=True, init=False)
    command_type: Mapped[CommandType] = mapped_column(String(16), index=True, init=False)
    command_args: Mapped[list[str]] = mapped_column(JSON, init=False)
    game_user: Mapped[BaseUser] = mapped_column(PydanticType, init=False)
    processed_data: Mapped[BaseProcessedData] = mapped_column(PydanticType, init=False)
    finish_time: Mapped[datetime] = mapped_column(DateTime, init=False)
