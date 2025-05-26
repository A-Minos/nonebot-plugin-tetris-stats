from secrets import choice

from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import QryItrface, Uninfo
from nonebot_plugin_uninfo import User as UninfoUser
from nonebot_plugin_uninfo.orm import get_session_persist_id
from nonebot_plugin_user import User
from nonebot_plugin_waiter import suggest  # type: ignore[import-untyped]

from ...config.config import global_config
from ...db import query_bind_info, remove_bind, trigger
from ...utils.host import HostPage, get_self_netloc
from ...utils.image import get_avatar
from ...utils.lang import get_lang
from ...utils.render import Bind, render
from ...utils.render.schemas.base import People
from ...utils.screenshot import screenshot
from . import alc
from .api import Player
from .constant import GAME_TYPE


@alc.assign('TOP.unbind')
async def _(
    nb_user: User,
    event_session: Uninfo,
    interface: QryItrface,
):
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
            await UniMessage('您还未绑定 TOP 账号').finish()
        resp = await suggest('您确定要解绑吗?', ['是', '否'])
        if resp is None or resp.extract_plain_text() == '否':
            return
        player = Player(user_name=bind.game_account, trust=True)
        user = await player.user
        netloc = get_self_netloc()
        async with HostPage(
            await render(
                'v1/binding',
                Bind(
                    platform='TOP',
                    type='unlink',
                    user=People(
                        avatar=await get_avatar(
                            event_session.user,
                            'Data URI',
                            None,
                        ),
                        name=user.user_name,
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
                    prompt='top绑定{游戏ID}',
                    lang=get_lang(),
                ),
            )
        ) as page_hash:
            await UniMessage.image(raw=await screenshot(f'http://{netloc}/host/{page_hash}.html')).send()
        await remove_bind(session=session, user=nb_user, game_platform=GAME_TYPE)
