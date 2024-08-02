from nonebot_plugin_orm import Model
from sqlalchemy import String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from .typing import Template


class TETRIOUserConfig(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    query_template: Mapped[Template] = mapped_column(String(2))
