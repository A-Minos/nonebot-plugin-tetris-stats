from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from nonebot.compat import PYDANTIC_V2, type_validate_json
from nonebot_plugin_orm import Model
from pydantic import BaseModel, ValidationError
from sqlalchemy import JSON, DateTime, Dialect, String, TypeDecorator
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column
from typing_extensions import override

from ..utils.typedefs import AllCommandType, GameType


class PydanticType(TypeDecorator):
    impl = JSON

    @override
    def __init__(
        self,
        get_model: Sequence[Callable[[], Sequence[type[BaseModel]]]],
        models: set[type[BaseModel]],
        *args: Any,
        **kwargs: Any,
    ):
        self.get_model = get_model
        self._models = models
        super().__init__(*args, **kwargs)

    if PYDANTIC_V2:

        @override
        def process_bind_param(self, value: Any | None, dialect: Dialect) -> str:
            # 将 Pydantic 模型实例转换为 JSON
            if isinstance(value, tuple(self.models)):
                return value.model_dump_json(by_alias=True)  # type: ignore[union-attr]
            raise TypeError
    else:

        @override
        def process_bind_param(self, value: Any | None, dialect: Dialect) -> str:
            # 将 Pydantic 模型实例转换为 JSON
            if isinstance(value, tuple(self.models)):
                return value.json(by_alias=True)  # type: ignore[union-attr]
            raise TypeError

    @override
    def process_result_value(self, value: Any | None, dialect: Dialect) -> BaseModel:
        # 将 JSON 转换回 Pydantic 模型实例
        if isinstance(value, str | bytes):
            for i in self.models:
                try:
                    return type_validate_json(i, value)
                except ValidationError:  # noqa: PERF203
                    ...
        raise ValueError

    @property
    def models(self) -> tuple[type[BaseModel], ...]:
        models: set[type[BaseModel]] = set()
        for i in self.get_model:
            models.update(i())
        models.update(self._models)
        return tuple(models)


class Bind(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    game_platform: Mapped[GameType] = mapped_column(String(32))
    game_account: Mapped[str]


class TriggerHistoricalData(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    trigger_time: Mapped[datetime] = mapped_column(DateTime)
    session_persist_id: Mapped[int]
    game_platform: Mapped[GameType] = mapped_column(String(32), index=True)
    command_type: Mapped[AllCommandType] = mapped_column(String(16), index=True)
    command_args: Mapped[list[str]] = mapped_column(JSON)
    finish_time: Mapped[datetime] = mapped_column(DateTime)
