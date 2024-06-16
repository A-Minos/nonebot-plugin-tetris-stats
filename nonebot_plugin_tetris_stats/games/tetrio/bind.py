from asyncio import gather
from hashlib import md5
from urllib.parse import urlencode

from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_session import EventSession  # type: ignore[import-untyped]
from nonebot_plugin_session_orm import get_session_persist_id  # type: ignore[import-untyped]
from nonebot_plugin_user import User  # type: ignore[import-untyped]
from nonebot_plugin_userinfo import BotUserInfo, UserInfo  # type: ignore[import-untyped]

from ...db import BindStatus, create_or_update_bind, trigger
from ...utils.host import HostPage, get_self_netloc
from ...utils.image import get_avatar
from ...utils.render import Bind, render
from ...utils.render.schemas.base import Avatar, People
from ...utils.screenshot import screenshot
from . import alc
from .api import Player
from .constant import GAME_TYPE


@alc.assign('TETRIO.bind')
async def _(nb_user: User, account: Player, event_session: EventSession, bot_info: UserInfo = BotUserInfo()):  # noqa: B008
    async with trigger(
        session_persist_id=await get_session_persist_id(event_session),
        game_platform=GAME_TYPE,
        command_type='bind',
        command_args=[],
    ):
        user, user_info = await gather(account.user, account.get_info())
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
                        status='unknown',
                        user=People(
                            avatar=f'http://{netloc}/host/resource/tetrio/avatars/{user.ID}?{urlencode({"revision": user_info.data.user.avatar_revision})}'
                            if user_info.data.user.avatar_revision is not None
                            and user_info.data.user.avatar_revision != 0
                            else Avatar(type='identicon', hash=md5(user_info.data.user.id.encode()).hexdigest()),  # noqa: S324
                            name=user_info.data.user.username.upper(),
                        ),
                        bot=People(
                            avatar=await get_avatar(bot_info, 'Data URI', '../../static/logo/logo.svg'),
                            name=bot_info.user_name,
                        ),
                        command='io查我',
                    ),
                )
            ) as page_hash:
                await UniMessage.image(raw=await screenshot(f'http://{netloc}/host/{page_hash}.html')).finish()
