from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import async_scoped_session
from nonebot_plugin_user import User  # type: ignore[import-untyped]
from sqlalchemy import select

from . import alc
from .models import TETRIOUserConfig
from .typing import Template


@alc.assign('TETRIO.config')
async def _(user: User, session: async_scoped_session, template: Template):
    config = (await session.scalars(select(TETRIOUserConfig).where(TETRIOUserConfig.id == user.id))).one_or_none()
    if config is None:
        config = TETRIOUserConfig(id=user.id, query_template=template)
        session.add(config)
    else:
        config.query_template = template
    await session.commit()
    await UniMessage('配置成功').finish()
