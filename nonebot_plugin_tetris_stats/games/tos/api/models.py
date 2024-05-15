from datetime import datetime
from typing import Literal

from nonebot_plugin_orm import Model
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from ....db.models import PydanticType
from .schemas.user_info import UserInfoSuccess
from .schemas.user_profile import UserProfile


class TOSHistoricalData(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    user_unique_identifier: Mapped[str] = mapped_column(String(24), index=True)
    api_type: Mapped[Literal['User Info', 'User Profile']] = mapped_column(String(16), index=True)
    data: Mapped[UserInfoSuccess | UserProfile] = mapped_column(
        PydanticType(get_model=[], models={UserInfoSuccess, UserProfile})
    )
    update_time: Mapped[datetime] = mapped_column(DateTime, index=True)
