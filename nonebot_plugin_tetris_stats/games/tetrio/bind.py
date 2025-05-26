from hashlib import md5
from secrets import choice

from arclet.alconna import Arg, ArgFlag
from nonebot_plugin_alconna import Args, Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import QryItrface, Uninfo
from nonebot_plugin_uninfo import User as UninfoUser
from nonebot_plugin_uninfo.orm import get_session_persist_id
from nonebot_plugin_user import User
from yarl import URL

from ...config.config import global_config
from ...db import BindStatus, create_or_update_bind, trigger
from ...utils.host import HostPage, get_self_netloc
from ...utils.image import get_avatar
from ...utils.lang import get_lang
from ...utils.render import Bind, render
from ...utils.render.schemas.base import Avatar, People
from ...utils.screenshot import screenshot
from . import alc, command, get_player
from .api import Player
from .constant import GAME_TYPE

command.add(
    Subcommand(
        'bind',
        Args(
            Arg(
                'account',
                get_player,
                notice='TETR.IO 用户名 / ID',
                flags=[ArgFlag.HIDDEN],
            )
        ),
        help_text='绑定 TETR.IO 账号',
    )
)

alc.shortcut(
    '(?i:io)(?i:绑定|绑|bind)',
    command='tstats TETR.IO bind',
    humanized='io绑定',
)


@alc.assign('TETRIO.bind')
async def _(nb_user: User, account: Player, event_session: Uninfo, interface: QryItrface):
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='bind',
        command_args=[],
    ):
        user = await account.user
        async with get_session() as session:
            bind_status = await create_or_update_bind(
                session=session,
                user=nb_user,
                game_platform=GAME_TYPE,
                game_account=user.unique_identifier,
            )
        if bind_status in (BindStatus.SUCCESS, BindStatus.UPDATE):
            netloc = get_self_netloc()
            async with HostPage(
                await render(
                    'v1/binding',
                    Bind(
                        platform='TETR.IO',
                        type='unknown',
                        user=People(
                            avatar=str(
                                URL(f'http://{netloc}/host/resource/tetrio/avatars/{user.ID}')
                                % {'revision': avatar_revision}
                            )
                            if (avatar_revision := (await account.avatar_revision)) is not None and avatar_revision != 0
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
            ) as page_hash:
                await UniMessage.image(raw=await screenshot(f'http://{netloc}/host/{page_hash}.html')).finish()
