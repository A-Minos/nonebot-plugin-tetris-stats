from datetime import datetime
from typing import Literal

from nonebot_plugin_orm import Model
from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from ....db.models import PydanticType
from ....db.types import UTCDateTime
from .schemas.user_info import UserInfoSuccess
from .schemas.user_profile import UserProfile


class TOSHistoricalData(MappedAsDataclass, Model):
    __tablename__ = 'nb_t_tos_hist_data'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    user_unique_identifier: Mapped[str] = mapped_column(String(256), index=True)
    api_type: Mapped[Literal['User Info', 'User Profile']] = mapped_column(String(16), index=True)
    data: Mapped[UserInfoSuccess | UserProfile] = mapped_column(
        PydanticType(get_model=[], models={UserInfoSuccess, UserProfile})
    )
    update_time: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    query_params: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
