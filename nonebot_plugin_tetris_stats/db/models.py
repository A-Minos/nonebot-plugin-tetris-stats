from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from nonebot.adapters import Message
from nonebot.compat import PYDANTIC_V2, type_validate_json
from nonebot_plugin_orm import Model
from pydantic import BaseModel, ValidationError
from sqlalchemy import JSON, DateTime, Dialect, PickleType, String, TypeDecorator
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column
from typing_extensions import override

from ..game_data_processor.schemas import BaseProcessedData, BaseUser
from ..utils.typing import CommandType, GameType


class PydanticType(TypeDecorator):
    impl = JSON

    @override
    def __init__(self, get_model: Callable[[], Sequence[type[BaseModel]]], *args: Any, **kwargs: Any):
        self.get_model = get_model
        super().__init__(*args, **kwargs)

    if PYDANTIC_V2:

        @override
        def process_bind_param(self, value: Any | None, dialect: Dialect) -> str:
            # 将 Pydantic 模型实例转换为 JSON
            if isinstance(value, tuple(self.get_model())):
                return value.model_dump_json(by_alias=True)  # type: ignore[union-attr]
            raise TypeError
    else:

        @override
        def process_bind_param(self, value: Any | None, dialect: Dialect) -> str:
            # 将 Pydantic 模型实例转换为 JSON
            if isinstance(value, tuple(self.get_model())):
                return value.json(by_alias=True)  # type: ignore[union-attr]
            raise TypeError

    @override
    def process_result_value(self, value: Any | None, dialect: Dialect) -> BaseModel:
        # 将 JSON 转换回 Pydantic 模型实例
        if isinstance(value, str | bytes):
            for i in self.get_model():
                try:
                    return type_validate_json(i, value)
                except ValidationError:  # noqa: PERF203
                    ...
        raise ValueError


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
    user_unique_identifier: Mapped[str] = mapped_column(String(32), index=True, init=False)
    game_user: Mapped[BaseUser] = mapped_column(PydanticType(get_model=BaseUser.__subclasses__), init=False)
    processed_data: Mapped[BaseProcessedData] = mapped_column(
        PydanticType(get_model=BaseProcessedData.__subclasses__), init=False
    )
    finish_time: Mapped[datetime] = mapped_column(DateTime, init=False)
