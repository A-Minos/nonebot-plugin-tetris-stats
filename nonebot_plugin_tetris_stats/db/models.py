from datetime import datetime

from nonebot.adapters import Message
from nonebot_plugin_orm import Model
from sqlalchemy import JSON, DateTime, PickleType, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from ..game_data_processor import ProcessedData, User
from ..utils.typing import CommandType, GameType


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
    game_user: Mapped[User] = mapped_column(PickleType, init=False)
    processed_data: Mapped[ProcessedData] = mapped_column(PickleType, init=False)
    finish_time: Mapped[datetime] = mapped_column(DateTime, init=False)
