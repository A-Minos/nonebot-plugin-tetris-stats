from datetime import timedelta

from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import async_scoped_session
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_uninfo.orm import get_session_persist_id
from nonebot_plugin_user import User
from sqlalchemy import select

from ...db import trigger
from ...i18n import Lang
from . import alc
from .constant import GAME_TYPE
from .models import TOPUserConfig


@alc.assign('TOP.config')
async def _(user: User, session: async_scoped_session, event_session: Uninfo, compare: timedelta):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='config',
        command_args=[f'--default-compare {compare}'],
    ):
        config = (await session.scalars(select(TOPUserConfig).where(TOPUserConfig.id == user.id))).one_or_none()
        if config is None:
            config = TOPUserConfig(id=user.id, compare_delta=compare)
            session.add(config)
        else:
            config.compare_delta = compare
        await session.commit()
        await UniMessage(Lang.bind.config_success()).finish()
