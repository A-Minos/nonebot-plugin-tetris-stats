from datetime import timezone

from arclet.alconna import Arg, ArgFlag
from nonebot import get_driver
from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import Args, At, Option, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from nonebot_plugin_user import User as NBUser
from nonebot_plugin_user import get_user
from sqlalchemy import select

from ....db import query_bind_info, trigger
from ....i18n import Lang
from ....utils.exception import FallbackError
from ....utils.typedefs import Me
from ... import add_block_handlers, alc
from .. import command, get_player
from ..api import Player
from ..constant import GAME_TYPE
from ..models import TETRIOUserConfig
from ..typedefs import Template
from .v1 import make_query_image_v1
from .v2 import make_query_image_v2

UTC = timezone.utc

driver = get_driver()

command.add(
    Subcommand(
        'query',
        Args(
            Arg(
                'target',
                At | Me,
                notice='@想要查询的人 / 自己',
                flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
            ),
            Arg(
                'account',
                get_player,
                notice='TETR.IO 用户名 / ID',
                flags=[ArgFlag.HIDDEN, ArgFlag.OPTIONAL],
            ),
        ),
        Option(
            '--template',
            Arg('template', Template),
            alias=['-T'],
            help_text='要使用的查询模板',
        ),
        help_text='查询 TETR.IO 游戏信息',
    ),
)

alc.shortcut(
    '(?i:io)(?i:查询|查|query|stats)',
    command='tstats TETR.IO query',
    humanized='io查',
)
alc.shortcut(
    'fkosk',
    command='tstats TETR.IO query',
    arguments=['我'],
    fuzzy=False,
    humanized='An Easter egg!',
)

add_block_handlers(alc.assign('TETRIO.query'))


async def make_query_result(player: Player, template: Template) -> UniMessage:
    if template == 'v1':
        try:
            return UniMessage.image(raw=await make_query_image_v1(player))
        except FallbackError:
            template = 'v2'
    if template == 'v2':
        return UniMessage.image(raw=await make_query_image_v2(player))
    return None


@alc.assign('TETRIO.query')
async def _(  # noqa: PLR0913
    user: NBUser,
    event: Event,
    matcher: Matcher,
    target: At | Me,
    event_session: EventSession,
    template: Template | None = None,
):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[f'--template {template}'] if template is not None else [],
    ):
        async with get_session() as session:
            bind = await query_bind_info(
                session=session,
                user=await get_user(
                    event_session.platform, target.target if isinstance(target, At) else event.get_user_id()
                ),
                game_platform=GAME_TYPE,
            )
            if template is None:
                template = await session.scalar(
                    select(TETRIOUserConfig.query_template).where(TETRIOUserConfig.id == user.id)
                )
        if bind is None:
            await matcher.finish('未查询到绑定信息')
        player = Player(user_id=bind.game_account, trust=True)
        await (
            UniMessage.i18n(Lang.interaction.warning.unverified) + await make_query_result(player, template or 'v1')
        ).finish()


@alc.assign('TETRIO.query')
async def _(user: NBUser, account: Player, event_session: EventSession, template: Template | None = None):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='query',
        command_args=[f'--template {template}'] if template is not None else [],
    ):
        async with get_session() as session:
            if template is None:
                template = await session.scalar(
                    select(TETRIOUserConfig.query_template).where(TETRIOUserConfig.id == user.id)
                )
        await (await make_query_result(account, template or 'v1')).finish()
