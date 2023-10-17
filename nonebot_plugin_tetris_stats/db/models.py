from datetime import datetime

from nonebot_plugin_orm import Model
from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..utils.typing import CommandType, GameType


class Bind(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    qq_number: Mapped[str] = mapped_column(index=True)
    IO_id: Mapped[str | None]
    TOP_id: Mapped[str | None]


class HistoricalData(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    trigger_time: Mapped[datetime] = mapped_column(DateTime)
    bot_platform: Mapped[str] = mapped_column(String(32))
    bot_id: Mapped[str] = mapped_column(String(64))
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str]
    message_id: Mapped[str] = mapped_column(String(64))
    game_type: Mapped[GameType] = mapped_column(String(16), index=True)
    command_type: Mapped[CommandType] = mapped_column(String(16), index=True)
    command_args: Mapped[list[str]] = mapped_column(JSON)
    game_user: Mapped[dict[str, str]] = mapped_column(JSON)
    processed_data: Mapped[dict[str, str]] = mapped_column(JSON)
    return_message: Mapped[bytes]
    finish_time: Mapped[datetime] = mapped_column(DateTime)
