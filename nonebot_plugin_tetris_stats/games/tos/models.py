from datetime import timedelta

from nonebot_plugin_orm import Model
from sqlalchemy import Interval
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column


class TOSUserConfig(MappedAsDataclass, Model):
    __tablename__ = 'nb_t_tos_u_cfg'

    id: Mapped[int] = mapped_column(primary_key=True)
    compare_delta: Mapped[timedelta | None] = mapped_column(Interval(native=True), nullable=True)
