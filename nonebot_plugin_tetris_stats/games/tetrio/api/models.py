from datetime import datetime
from typing import Literal

from nonebot_plugin_orm import Model
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from ....db.models import PydanticType
from .schemas.base import SuccessModel


class TETRIOHistoricalData(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    user_unique_identifier: Mapped[str] = mapped_column(String(24), index=True)
    api_type: Mapped[Literal['User Info', 'User Records']] = mapped_column(String(16), index=True)
    data: Mapped[SuccessModel] = mapped_column(PydanticType(get_model=[SuccessModel.__subclasses__], models=set()))
    update_time: Mapped[datetime] = mapped_column(DateTime, index=True)
