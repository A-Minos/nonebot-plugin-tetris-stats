from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import async_scoped_session
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from nonebot_plugin_user import User  # type: ignore[import-untyped]
from sqlalchemy import select

from ...db import trigger
from . import alc
from .constant import GAME_TYPE
from .models import TETRIOUserConfig
from .typing import Template


@alc.assign('TETRIO.config')
async def _(user: User, session: async_scoped_session, event_session: EventSession, template: Template):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='config',
        command_args=[f'--default-template {template}'],
    ):
        config = (await session.scalars(select(TETRIOUserConfig).where(TETRIOUserConfig.id == user.id))).one_or_none()
        if config is None:
            config = TETRIOUserConfig(id=user.id, query_template=template)
            session.add(config)
        else:
            config.query_template = template
        await session.commit()
        await UniMessage('配置成功').finish()
