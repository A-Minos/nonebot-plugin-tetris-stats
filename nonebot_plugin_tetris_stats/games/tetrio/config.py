from datetime import timedelta

from arclet.alconna import Arg
from nonebot_plugin_alconna import Option, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import async_scoped_session
from nonebot_plugin_uninfo import Uninfo
from nonebot_plugin_uninfo.orm import get_session_persist_id
from nonebot_plugin_user import User
from sqlalchemy import select

from ...db import trigger
from ...i18n import Lang
from ...utils.duration import parse_duration
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
        Option(
            '--default-compare',
            Arg('compare', parse_duration, notice='对比时间距离'),
            alias=['-DC', 'DefaultCompare'],
            help_text='设置默认对比时间距离',
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
async def _(
    user: User,
    session: async_scoped_session,
    event_session: Uninfo,
    template: Template | None = None,
    compare: timedelta | None = None,
):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='config',
        command_args=([f'--default-template {template}'] if template is not None else [])
        + ([f'--default-compare {compare}'] if compare is not None else []),
    ):
        config = (await session.scalars(select(TETRIOUserConfig).where(TETRIOUserConfig.id == user.id))).one_or_none()
        if config is None:
            config = TETRIOUserConfig(id=user.id, query_template=template or 'v1', compare_delta=compare)
            session.add(config)
        else:
            if template is not None:
                config.query_template = template
            if compare is not None:
                config.compare_delta = compare
        await session.commit()
        await UniMessage(Lang.bind.config_success()).finish()
