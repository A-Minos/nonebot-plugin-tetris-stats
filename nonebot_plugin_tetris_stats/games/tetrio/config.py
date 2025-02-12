from arclet.alconna import Arg
from nonebot_plugin_alconna import Option, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import async_scoped_session
from nonebot_plugin_session import EventSession
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from nonebot_plugin_user import User
from sqlalchemy import select

from ...db import trigger
from . import alc, command
from .constant import GAME_TYPE
from .models import TETRIOUserConfig
from .typedefs import Template

command.add(
    Subcommand(
        'config',
        Option(
            '--default-template',
            Arg('template', Template, notice='模板版本'),
            alias=['-DT', 'DefaultTemplate'],
            help_text='设置默认查询模板',
        ),
        help_text='TETR.IO 查询个性化配置',
    ),
)

alc.shortcut(
    '(?i:io)(?i:配置|配|config)',
    command='tstats TETR.IO config',
    humanized='io配置',
)


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
