from secrets import choice

from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import QryItrface, Uninfo
from nonebot_plugin_uninfo import User as UninfoUser
from nonebot_plugin_uninfo.orm import get_session_persist_id
from nonebot_plugin_user import User

from ...config.config import global_config
from ...db import BindStatus, create_or_update_bind, trigger
from ...i18n import Lang
from ...utils.image import get_avatar
from ...utils.lang import get_lang
from ...utils.render import render_image
from ...utils.render.schemas.base import People
from ...utils.render.schemas.bind import Bind
from . import alc
from .api import Player
from .constant import GAME_TYPE


@alc.assign('TOS.bind')
async def _(
    nb_user: User,
    account: Player,
    event_session: Uninfo,
    interface: QryItrface,
):
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
        user_info = await account.get_info()
        if bind_status in (BindStatus.SUCCESS, BindStatus.UPDATE):
            await UniMessage.image(
                raw=await render_image(
                    Bind(
                        platform=GAME_TYPE,
                        type='unknown',
                        user=People(
                            avatar=await get_avatar(
                                event_session.user,
                                'Data URI',
                                None,
                            ),
                            name=user_info.data.name,
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
                        prompt=Lang.prompt.tos_check(),
                        lang=get_lang(),
                    ),
                )
            ).finish()
