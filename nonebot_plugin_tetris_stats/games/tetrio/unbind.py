from hashlib import md5
from secrets import choice

from nonebot_plugin_alconna import Subcommand
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import QryItrface, Uninfo
from nonebot_plugin_uninfo import User as UninfoUser
from nonebot_plugin_uninfo.orm import get_session_persist_id
from nonebot_plugin_user import User
from nonebot_plugin_waiter import suggest  # type: ignore[import-untyped]
from yarl import URL

from ...config.config import global_config
from ...db import query_bind_info, remove_bind, trigger
from ...i18n import Lang
from ...utils.host import get_self_netloc
from ...utils.image import get_avatar
from ...utils.lang import get_lang
from ...utils.render import render_image
from ...utils.render.schemas.base import Avatar, People
from ...utils.render.schemas.bind import Bind
from . import alc, command
from .api import Player
from .constant import GAME_TYPE

command.add(Subcommand('unbind', help_text='解除绑定 TETR.IO 账号'))

alc.shortcut(
    '(?i:io)(?i:解除绑定|解绑|unbind)',
    command='tstats TETR.IO unbind',
    humanized='io解绑',
)


@alc.assign('TETRIO.unbind')
async def _(nb_user: User, event_session: Uninfo, interface: QryItrface):
    async with (
        trigger(
            session_persist_id=await get_session_persist_id(event_session),
            game_platform=GAME_TYPE,
            command_type='unbind',
            command_args=[],
        ),
        get_session() as session,
    ):
        if (bind := await query_bind_info(session=session, user=nb_user, game_platform=GAME_TYPE)) is None:
            await UniMessage(Lang.bind.no_account(game='TETR.IO')).finish()
        resp = await suggest(Lang.bind.confirm_unbind(), ['是', '否'])
        if resp is None or resp.extract_plain_text() == '否':
            return
        player = Player(user_id=bind.game_account, trust=True)
        user = await player.user
        netloc = get_self_netloc()
        await UniMessage.image(
            raw=await render_image(
                Bind(
                    platform='TETR.IO',
                    type='unlink',
                    user=People(
                        avatar=str(
                            URL(f'http://{netloc}/host/resource/tetrio/avatars/{user.ID}')
                            % {'revision': avatar_revision}
                        )
                        if (avatar_revision := (await player.avatar_revision)) is not None and avatar_revision != 0
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
                    prompt=Lang.prompt.io_bind(),
                    lang=get_lang(),
                ),
            )
        ).send()
        await remove_bind(session=session, user=nb_user, game_platform=GAME_TYPE)
