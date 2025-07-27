from asyncio import gather
from hashlib import md5
from secrets import choice

from nonebot_plugin_alconna import Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import QryItrface, Uninfo
from nonebot_plugin_uninfo import User as UninfoUser
from nonebot_plugin_uninfo.orm import get_session_persist_id
from nonebot_plugin_user import User
from yarl import URL

from ...config.config import global_config
from ...db import create_or_update_bind, query_bind_info, trigger
from ...utils.host import get_self_netloc
from ...utils.image import get_avatar
from ...utils.lang import get_lang
from ...utils.render import render_image
from ...utils.render.schemas.base import Avatar, People
from ...utils.render.schemas.bind import Bind
from . import alc, command
from .api import Player
from .constant import GAME_TYPE

command.add(Subcommand('verify', help_text='验证 TETR.IO 账号'))

alc.shortcut(
    '(?i:io)(?i:验证|verify)',
    command='tstats TETR.IO verify',
    humanized='io验证',
)

try:
    from nonebot.adapters.discord import MessageCreateEvent

    @alc.assign('TETRIO.verify')
    async def _(_: MessageCreateEvent, nb_user: User, event_session: Uninfo, interface: QryItrface):
        async with (
            trigger(
                session_persist_id=await get_session_persist_id(event_session),
                game_platform=GAME_TYPE,
                command_type='verify',
                command_args=[],
            ),
            get_session() as session,
        ):
            if (bind := await query_bind_info(session=session, user=nb_user, game_platform=GAME_TYPE)) is None:
                await UniMessage('您还未绑定 TETR.IO 账号').finish()
            if bind.verify is True:
                await UniMessage('您已经完成了验证.').finish()
            player = Player(user_id=bind.game_account, trust=True)
            user_info = await player.get_info()
            verify = (
                user_info.data.connections.discord is not None
                and user_info.data.connections.discord.id == event_session.user.id
            )
            if verify is False:
                await UniMessage('您未通过验证, 请确认目标 TETR.IO 账号绑定了当前 Discord 账号').finish()
            await create_or_update_bind(
                session=session,
                user=nb_user,
                game_platform=GAME_TYPE,
                game_account=bind.game_account,
                verify=verify,
            )
            user, avatar_revision = await gather(player.user, player.avatar_revision)
            await UniMessage.image(
                raw=await render_image(
                    Bind(
                        platform='TETR.IO',
                        type='success',
                        user=People(
                            avatar=str(
                                URL(f'http://{get_self_netloc()}/host/resource/tetrio/avatars/{user.ID}')
                                % {'revision': avatar_revision}
                            )
                            if avatar_revision is not None and avatar_revision != 0
                            else Avatar(type='identicon', hash=md5(user.ID.encode()).hexdigest()),  # noqa: S324
                            name=user.name.upper(),
                        ),
                        bot=People(
                            avatar=await get_avatar(
                                (
                                    bot_user := await interface.get_user(event_session.self_id)
                                    or UninfoUser(id=event_session.self_id)
                                ),
                                'Data URI',
                                '../../static/logo/logo.svg',
                            ),
                            name=bot_user.nick or bot_user.name or choice(list(global_config.nickname) or ['bot']),
                        ),
                        prompt='io查我',
                        lang=get_lang(),
                    ),
                )
            ).finish()
except ImportError:
    pass


@alc.assign('TETRIO.verify')
async def _(event_session: Uninfo):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='verify',
        command_args=[],
    ):
        await UniMessage('目前仅支持 Discord 账号验证').finish()
