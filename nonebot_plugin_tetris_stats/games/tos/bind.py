from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from nonebot_plugin_user import User
from nonebot_plugin_userinfo import BotUserInfo, EventUserInfo, UserInfo

from ...db import BindStatus, create_or_update_bind, trigger
from ...utils.host import HostPage, get_self_netloc
from ...utils.image import get_avatar
from ...utils.lang import get_lang
from ...utils.render import Bind, render
from ...utils.render.schemas.base import People
from ...utils.screenshot import screenshot
from . import alc
from .api import Player
from .constant import GAME_TYPE


@alc.assign('TOS.bind')
async def _(
    nb_user: User,
    account: Player,
    event_session: EventSession,
    event_user_info: UserInfo = EventUserInfo(),  # noqa: B008
    bot_info: UserInfo = BotUserInfo(),  # noqa: B008
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
            async with HostPage(
                await render(
                    'v1/binding',
                    Bind(
                        platform=GAME_TYPE,
                        type='unknown',
                        user=People(
                            avatar=await get_avatar(event_user_info, 'Data URI', None), name=user_info.data.name
                        ),
                        bot=People(
                            avatar=await get_avatar(bot_info, 'Data URI', '../../static/logo/logo.svg'),
                            name=bot_info.user_remark or bot_info.user_displayname or bot_info.user_name,
                        ),
                        prompt='茶服查我',
                        lang=get_lang(),
                    ),
                )
            ) as page_hash:
                await UniMessage.image(
                    raw=await screenshot(f'http://{get_self_netloc()}/host/{page_hash}.html')
                ).finish()
